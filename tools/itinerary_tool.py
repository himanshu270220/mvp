from openai import AzureOpenAI, OpenAI
from opik.integrations.openai import track_openai
from opik import track
import json
import os
from dotenv import load_dotenv
from api.clients.itinerary_api import ItineraryAPI
from tools.redis_cache import RedisCache

load_dotenv()

class ItineraryTool:
    def __init__(self, client_type="openai"):
        self.cache = RedisCache()
        self.itinerary_api = ItineraryAPI()
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.api_key = os.getenv('OPENAI_API_KEY')
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

    @track
    def add_itinerary(self, destination: str, itinerary: list) -> bool:
        """
        Add a new itinerary for a destination
        """
        try:
            self.itineraries[destination.lower()] = itinerary
            return True
        except Exception as e:
            print(f"Error adding itinerary: {str(e)}")
            return False

    @track
    def get_itinerary(self, destination: str, user_id: str) -> list:
        """
        Get itinerary for a specific destination
        
        Args:
            destination: Name of the destination
            
        Returns:
            list: Object of day-wise itinerary items if found, empty object otherwise
        """
        try:
            exisiting_itinerary = self.itinerary_api.get_base_itinerary(destination.lower())
            self.cache.set(user_id + '-' + exisiting_itinerary.get('itinerary_id', ''), exisiting_itinerary)
            return f'base_itinerary: {json.dumps(exisiting_itinerary, indent=2)}'
        except Exception as e:
            print(f"Error getting itinerary: {str(e)}")
            return 'Error getting itinerary'
    
    @track
    def get_base_itinerary(
        self,
        destination: str,
        activities: any,
        hotels: any,
        number_of_days: int
    ):
        """
        Get base itinerary for a specific destination
        
        Args:
            destination: Name of the destination
            activities: List of activities
            hotels: List of hotels
            number_of_days: Number of days to plan for
            
        Returns:
            list: Object of day-wise itinerary items if found, empty object otherwise
        """
        try:
            system_prompt = """You are world class trip itinerary builder, 
            Your task is to create customized itinerary for a user based on the information provided to you about the destination,
            activities, hotels and number of days. Make sure to arrange hotels and activities based on number of days.
            activities will have duration as well, so adjust the itinerary accordingly. Make sure, not to distribute same activities in different days. If you think something can not be accomodated, then add it to the exclusions.
            It is strictly important not to include another information part from what is provided to you about activities, hotel. Add nothing else.
            Don't include information like breakfast, lunch, dinner, etc. in the itinerary. Add activities only.
            Create concise but efficient trip itinerary for a user and give user a would class experience.
            
            it should be json in the following format:
            {{
                "trip": {{
                    "destination": "destination",
                    "itinerary": [
                        {{
                            "day": 1,
                            "hotel": {{
                                "name": "hotel_name",
                                "description": "hotel_description",
                                "rating": 4.8
                            }},
                            "activities": [
                                {{
                                    "time": "08:00",
                                    "activity": "Breakfast",
                                    "acitivity_image_url": "activity_image_url",
                                    "activity_duration": 60,
                                    "details": "Try local specialties like XYZ"
                                }},
                                {{
                                    "time": "10:00",
                                    "activity": "abc",
                                    "details": "Try local specialties like XYZ"
                                }},
                            ]
                        }},
                        {{
                            "day": 2,
                            "activities": [
                                {{
                                    "time": "08:00",
                                    "activity": "Breakfast",
                                    "details": "Try local specialties like XYZ"
                                }},
                            ]
                        }}
                    ],
                    "exclusions": [
                        "Visa on arrival fee",
                        "Personal expenses",
                        "Additional activities",
                        "Tips for drivers and guides",
                        "Meals not mentioned"
                    ]
                }}
            }}
            """

            response = self.client.chat.completions.create(
                model='gpt-4o',
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
            )
            message = response.choices[0].message.content
            return message
        except Exception as e:
            print(f"Error getting itinerary: {str(e)}")
            return 'Error getting itinerary'
    
    @track
    async def add_changes_to_itinerary(self, user_id: str, itinerary_id: str, changes) -> bool:
        """
        Add changes to intermediate itinerary
        """
        try:
            self.itinerary_api.update_itinerary(changes, itinerary_id, user_id)
            return True
        except Exception as e:
            print(f"Error saving itinerary: {str(e)}")
            return False

    @track
    def save_itinerary(self, user_id: str, itinerary_id: str, changes) -> bool:
       
        try:
            self.itinerary_api.update_itinerary(changes, itinerary_id, user_id)
            return True
        except Exception as e:
            print(f"Error saving itinerary: {str(e)}")
            return False