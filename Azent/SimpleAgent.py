from typing import Dict, Any
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
load_dotenv()


class SimpleAgent:
    """
    A simple agent class that can be instantiated with configuration and used directly.
    """

    def __init__(
            self,
            system_prompt: str,
            output_format: Dict[str, Any] = None,
            base_url: str = None,
            api_key: str = None,
            model: str = None,
            temperature: float = 0.6,
    ):
        """
        Initialize the agent with configuration.

        Args:
            system_prompt: The system prompt that defines the agent's behavior
            output_format: Expected format of the output (e.g., {"type": "json_object"})
            base_url: OpenAI API base URL
            api_key: OpenAI API key
            model: Model to use
            temperature: Temperature for response generation
        """
        self.system_prompt = system_prompt
        self.output_format = output_format
        self.temperature = temperature

        self.client = OpenAI(
            base_url=base_url or os.getenv('LLM_BASE_URL'),
            api_key=api_key or os.getenv('LLM_API_KEY')
        )
        self.model = model or os.getenv('SCRATCH_MODEL')

    def execute(self, user_input: str) -> Any:
        """
        Execute the agent with the given input.

        Args:
            user_input: The input string for the agent

        Returns:
            The response from the agent (format depends on output_format)
        """
        completion_args = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self.system_prompt,
                },
                {
                    "role": "user",
                    "content": user_input
                }
            ],
            "temperature": self.temperature,
        }

        if self.output_format:
            completion_args["response_format"] = self.output_format

        response = self.client.chat.completions.create(**completion_args)
        content = response.choices[0].message.content

        # If JSON output was requested, parse the response
        if self.output_format and self.output_format.get("type") == "json_object":
            clean_response = content.replace('json', '').replace('```', '')
            return json.loads(clean_response)

        return content