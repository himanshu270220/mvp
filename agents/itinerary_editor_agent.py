from dotenv import load_dotenv
from Azent.Azent import Agent
from prompts.get_itinerary_editor_prompt import get_itinerary_editor_prompt
from tools.get_activities_tool import get_activities_by_activity_name, \
    get_activities_by_group_type_or_travel_theme_and_number_of_days
from tools.get_hotels_tool import get_hotels_by_destination, get_hotels
from opik import track
import os

from tools.itinerary_tool import ItineraryTool
from tools.redis_cache import RedisCache


class ItineraryEditorAgent:
    """Class to handle the conversation management using the custom Agent class"""

    def __init__(self, itinerary_id: str):
        load_dotenv()
        self.redis_cache = RedisCache()
        self.package = self.redis_cache.get(itinerary_id)
        self.itinerary_id = itinerary_id

    @track
    def get_or_create_agent(self, session_id: str) -> Agent:
        """Get existing agent or create new one for the user"""
        try:
            new_agent = Agent(
                name='itinerary editor agent',
                model=os.getenv('ITINERARY_EDITOR_MODEL'),
                instructions=get_itinerary_editor_prompt(self.package),
                session_id=session_id,
                tools=[
                    get_hotels,
                    ItineraryTool(itinerary_id=self.itinerary_id).update_itinerary
                ],
            )
            return new_agent
        except Exception as e:
            print(e)
            raise e

    @track
    def generate_response(self, session_id: str, user_input: str) -> str:
        """Generate response using the itinerary agent"""
        agent = self.get_or_create_agent(session_id)
        print("agent", agent.name)
        try:
            thread = agent.run(user_input)
            return [msg for msg in thread if msg['role'] != 'system']

        except Exception as e:
            print(f"Error generating response: {e}")
            return "I apologize, but I encountered an error processing your request. Please try again."

    def clear_conversation(self, user_id: str) -> None:
        """Clear user's conversation by removing their agent"""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
