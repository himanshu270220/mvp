from dotenv import load_dotenv
from Azent.Azent import Agent
from prompts.get_base_itinerary_editor_prompt import get_base_itinerary_prompt
from tools.itinerary_tool import ItineraryTool
from opik import track
import os


class BaseItineraryAgent:
    """Class to handle the conversation management using the custom Agent class"""

    def __init__(self):
        load_dotenv()

    @track
    def get_or_create_agent(self, session_id: str) -> Agent:
        """Get existing agent or create new one for the user"""
        try:
            new_agent = Agent(
                name='base itinerary agent',
                model=os.getenv('BASE_ITINERARY_MODEL'),
                instructions=get_base_itinerary_prompt(session_id),
                session_id=session_id,
                tools=[
                    ItineraryTool().get_base_itinerary
                ],
            )
            return new_agent
        except Exception as e:
            print(e)
            raise e

    @track
    def generate_response(self, session_id: str, user_input: str) -> str:
        """Generate response using the manager agent"""
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
