import datetime
import json
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from Azent.Azent import Agent
from opik.integrations.openai import track_openai
from opik import track
from api.clients.itinerary_api import ItineraryAPI
from tools.redis_cache import RedisCache
from dotenv import load_dotenv

load_dotenv()

class UserItineraryAgent:
    def __init__(self):
        load_dotenv()
        self.active_sessions: Dict[str, Agent] = {}
        self.session_state: Dict[str, Dict[str, Any]] = {}
        self.cache = RedisCache()
        self.itinerary_api = ItineraryAPI()

    @track
    def get_or_create_agent(self) -> Agent:
        """Get or create an agent for handling user's itinerary updates"""
        new_agent = Agent(
                name='personal itinerary agent',
                model="gpt-4o",
                instructions=f'''
                You are a personal itinerary customization agent.
                Your task is to create a trip itinerary based on the user's preferences.
                You will get destination, activities  and hotels information from the user.
                You will get acitivities with duration, so adjust the itinerary accordingly.

                It may possible that activities and hotels are not available in the destination. 
                In this case, you should use best of your knowledge to add activities and hotels.

                Important guidelines:
                - Consider logical flow of activities
                '''
            )
        return new_agent

    @track
    def finalize_itinerary(
            self, 
            session_id: str,
            update_request: str
    ) -> Dict[str, Any]:
        """Process a user's itinerary update request"""
        try:
            agent = self.get_or_create_agent(session_id)

            prompt = f"""
            Please analyze this user's preferences and create a personalized itinerary for it:
            {update_request}

            return the updated itinerary in same JSON format existing_itinerary.
            """
            
            response = agent.run(prompt, response_format="json")
            self.cache.set('itinerary:' + session_id + json.loads(response[-1].get('content', '')))
            return response
            
        except Exception as e:
            print(f"Error processing update request: {e}")
            return {
                "status": "error",
                "message": "Failed to process update request",
                "error": str(e)
            }

    def get_update_history(self, user_id: str, destination: str) -> List[Dict[str, Any]]:
        """Get history of updates for user's itinerary"""
        try:
            current_itinerary = self._call_api(f"/api/users/{user_id}/itineraries/{destination}")
            version = current_itinerary.get('metadata', {}).get('version', 1)
            
            return {
                "current_version": version,
                "last_modified": current_itinerary.get('metadata', {}).get('last_modified'),
                "has_customizations": version > 1
            }
        except Exception as e:
            print(f"Error fetching update history: {e}")
            return {
                "error": "Could not fetch update history",
                "details": str(e)
            }

    def clear_session(self, user_id: str) -> None:
        """Clear user's session and state"""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
        if user_id in self.session_state:
            del self.session_state[user_id]