from openai import AzureOpenAI, OpenAI
from opik.integrations.openai import track_openai
from opik import track
import json
import os
from dotenv import load_dotenv

from tools.get_activities_tool import get_activities_by_group_type_or_travel_theme_and_number_of_days
from tools.get_hotels_tool import get_hotels_by_destination
from tools.redis_cache import RedisCache
import uuid
import inspect
import re
load_dotenv()


class ItineraryTool:
    def __init__(self, client_type="openai"):
        self.cache = RedisCache()
        self.base_url = os.getenv("LLM_BASE_URL")
        self.api_key = os.getenv('LLM_API_KEY')
        self.client_type = os.getenv('LLM_CLIENT_TYPE')

        if self.client_type == "azure":
            self.client = AzureOpenAI(
                api_key=os.getenv('OPENAI_API_KEY'),
                azure_endpoint=os.getenv('OPENAI_BASE_URL'),
                azure_deployment='gpt-4o-mvp-dev',
                api_version='2024-02-15-preview'
            )
        else:
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )

    def get_uuid(self):
        return uuid.uuid4()

    def function_to_schema(self, func) -> dict:
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


    def execute_tool_call(self, tool_call, tools_map):
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)

        print(f"Assistant: {name}({args})")
        return tools_map[name](**args)

    @track
    def get_base_itinerary(
            self,
            destination: str,
            group_type: str,
            travel_theme: str,
            hote_star_rating: int,
            number_of_days: float,
    ):
        """
        Get base itinerary for a specific destination
        
        Args:
            destination: Name of the destination
            group_type: Type of the group
            travel_theme: Name of the travel theme
            number_of_days: Number of days to plan for
            
        Returns:
            list: Object of day-wise itinerary items if found, empty object otherwise
        """

        # get activities
        activities = get_activities_by_group_type_or_travel_theme_and_number_of_days(
            group_type=group_type,
            travel_theme=travel_theme,
            number_of_days=number_of_days,
            destination=destination
        )

        # get hotels
        hotels = get_hotels_by_destination(
            destination=destination,
            travel_theme=travel_theme,
            group_type=group_type,
            star_rating=hote_star_rating,
        )

        try:
            system_prompt = """You are world class trip itinerary builder, 
            Your task is to create customized itinerary for a user based on the information provided to you about the destination,
            activities, hotels and number of days. Make sure to arrange hotels and activities based on number of days.
            activities will have duration as well, so adjust the itinerary accordingly. Make sure, not to distribute same activities in different days. If you think something can not be accomodated, then add it to the exclusions.
            It is strictly important not to include another information part from what is provided to you about activities, hotel. Add nothing else.
            Don't include information like breakfast, lunch, dinner, etc. in the itinerary. Add activities only.
            Create concise but efficient trip itinerary for a user and give user a would class experience.
            keep id as <uuid>
            
            it should be json in the following format:
            {{
                "id": <uuid>
                "name": "Paris Adventure Package",
                "subtitle": "Experience the magic of Paris in 5 days",
                "image": "https://example.com/paris-skyline.jpg",
                "duration": 5,
                "itinerary_detail": [
                {{
            "active": true,
                    "description": "Day 1: Historical Paris Tour",
                    "details": [
                    {{
            "type": "activity",
                        "id": <uuid>,
                        "title": "Eiffel Tower Visit",
                        "description": "Skip-the-line access to Paris's most iconic monument",
                        "duration": "3 hours",
                        "image": "<image_url>"
                    }},
                    {{
            "type": "hotel",
                        "id": <uuid>,
                        "title": "Louvre Museum Tour",
                        "description": "Guided tour of world's largest art museum",
                        "rating": 4.9,
                        "image": "https://example.com/louvre.jpg"
                    }}
                    ]
                }},
                {{
            "active": false,
                    "description": "Day 2: Artistic Montmartre",
                    "details": [
                    {{
            "type": "activity",
                        "id": <uuid>,
                        "title": "Sacré-Cœur Basilica",
                        "description": "Visit the iconic white church with panoramic city views",
                        "duration": "2 hours",
                        "image": "<image_url>"
                    }},
                    {{
            "type": "activity",
                        "id": <uuid>,
                        "title": "Place du Tertre",
                        "description": "Experience the artist square and get your portrait drawn",
                        "rating": 4.6,
                        "image": "<image_url>"
                    }},
                    {{
            "type": "hotel",
                        "id": <uuid>,
                        "title": "Louvre Museum Tour",
                        "description": "Guided tour of world's largest art museum",
                        "rating": 4.9,
                        "image": "https://example.com/louvre.jpg"
                    }}
                    ]
                }}
                ]
            }}
            """

            response = self.client.chat.completions.create(
                model=os.getenv('ITINERARY_MODEL'),
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": f"""create itinerary for a user based on this information,
                        "destination": {destination},
                        "activities": {str(activities)},
                        "hotels": {str(hotels)},
                        "number_of_days": {str(number_of_days)}
                        """
                    }
                ],
                temperature=0.6,
                response_format={"type": "json_object"},
            )
            message = response.choices[0].message.content

            response = message.replace("```json\n", "").replace("\n```", "")
            response = self.replace_with_uuid(response)
            json_response = json.loads(response)
            return json_response
        except Exception as e:
            print(f"Error getting itinerary: {str(e)}")
            return 'Error getting itinerary'

    @track
    def replace_with_uuid(self, text):
        try:
            return re.sub(r"<id>", lambda _: str(uuid.uuid4()), text)
        except Exception as e:
            print(f"Error replacing itinerary: {str(e)}")
