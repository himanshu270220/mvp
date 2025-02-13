import openai
from pydantic import BaseModel
from typing import List, Optional
import json, os
import inspect
from opik.integrations.openai import track_openai
from opik import track
from openai import AzureOpenAI, OpenAI
from tools.redis_cache import RedisCache
from dotenv import load_dotenv
load_dotenv()

class Agent:

    def __init__(
            self, 
            name: str, 
            model: str, 
            instructions: str, 
            session_id=None,
            temperature=1,
            tools=[], 
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv('OPENAI_API_KEY'),
            client_type=os.getenv('LLM_CLIENT_TYPE'),
    ):

        # Open AI client
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )

        if client_type == "azure":
            self.client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=base_url,
                azure_deployment='gpt-4o-mvp-dev',
                api_version='2024-02-15-preview'
            )

        self.redis_cache = RedisCache()
        # Agent Attributes
        self.name = name
        self.model = model
        self.instructions = instructions

        self.tools = tools
        self.session_id = session_id

        # if tools provided then create a tool map {tool name: tool object}
        if self.tools != []:
            # Creating a tool map
            self.tools_map = {tool.__name__: tool for tool in self.tools}
        
        self.temp = temperature

        self.thread = self.redis_cache.get('conversation:' + self.session_id)
        if self.thread == None:
            self.thread = [{"role":"system","content":self.instructions}]
  
    def function_to_schema(self,func) -> dict:
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            type(None): "null",
        }

        try:
            signature = inspect.signature(func)
        except ValueError as e:
            raise ValueError(
                f"Failed to get signature for function {func.__name__}: {str(e)}"
            )

        parameters = {}
        for param in signature.parameters.values():
            try:
                param_type = type_map.get(param.annotation, "string")
            except KeyError as e:
                raise KeyError(
                    f"Unknown type annotation {param.annotation} for parameter {param.name}: {str(e)}"
                )
            parameters[param.name] = {"type": param_type}

        required = [
            param.name
            for param in signature.parameters.values()
            if param.default == inspect._empty
        ]

        return {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": (func.__doc__ or "").strip(),
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required,
                },
            },
        }
    
    @track
    def execute_tool_call(self, tool_call, tools_map):
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)

        print(f"Assistant: {name}({args})")
        return tools_map[name](**args)

    def tools_to_toolschema(self) -> list:
        # for tool in self.tools:
        #     print(tool)
        return [self.function_to_schema(tool) for tool in self.tools]
    
    @track
    def run(self, query, response_format=None, max_tool_calls=1):
        """
        Run the agent with fixed tool calling sequence
        """
        try:
            self.thread.append({"role": "user", "content": query})
            
            if not self.tools:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.thread,
                    temperature=self.temp,
                    response_format={'type': 'json_object'} if response_format == 'json' else None
                )
                message = response.choices[0].message.content
                self.thread.append({"role": "assistant", "content": str(message)})
                self.save_thread()
                return self.thread

            tool_schemas = self.tools_to_toolschema()
            tools_map = {tool.__name__: tool for tool in self.tools}
            tool_call_count = 0
            
            while tool_call_count < max_tool_calls:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.thread,
                    tools=tool_schemas,
                    temperature=self.temp,
                    response_format={'type': 'json_object'} if response_format == 'json' else None
                )
                
                message = response.choices[0].message
                
                assistant_message = {
                    "role": "assistant",
                    "content": message.content if message.content else None,
                    "type": "text"
                }
                
                if message.tool_calls:
                    assistant_message["tool_calls"] = [
                        {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                        for tool_call in message.tool_calls
                    ]
                
                self.thread.append(assistant_message)
                
                if not message.tool_calls:
                    break
                
                for tool_call in message.tool_calls:
                    if tool_call.function.name in tools_map:
                        try:
                            result = self.execute_tool_call(tool_call, tools_map)
                            tool_response = {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_call.function.name,
                                "content": json.dumps(result) if result is not None else "{}",
                                "type": "json" if tool_call.function.name in ['get_activities_by_group_type_or_travel_theme', 'get_hotels_by_destination'] else "text"
                            }
                            self.thread.append(tool_response)
                        except Exception as e:
                            print(f"Tool execution error: {str(e)}")
                            tool_response = {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_call.function.name,
                                "content": json.dumps({"error": str(e)})
                            }
                            self.thread.append(tool_response)
                    else:
                        print(f"Warning: Tool {tool_call.function.name} not found!")
                
                tool_call_count += 1
            
            self.save_thread()
            return self.thread
        
        except Exception as e:
            print('Exception occurred:', e)
            raise
        
    def get_thread(self):
        return self.thread
    
    def save_thread(self):
        self.redis_cache.set('conversation:' + self.session_id, self.thread)

    def call_function(self,resp):
        "This method is used to call the tool from the llms response"

        message = resp.choices[0].message

        function = message.tool_calls[0].function

        name = function.name
        args = json.loads(function.arguments)

        return self.tools_map[name](**args)
    

    def run_pyd(self, query, pyd_model) -> dict:
        "This method is to use pydantic models for getting structured outputs"

        self.thread.append({"role":"user","content":query})

        response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=self.thread,
                response_format=pyd_model,
                temperature=self.temp
                )
        
        struct_msg = response.choices[0].message.parsed.model_dump()

        return struct_msg