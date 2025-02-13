from ..base import BaseAPIClient
from typing import Dict

class ItineraryAPI(BaseAPIClient):
    def __init__(self):
        super().__init__('itinerary')

    def health_check(self) -> bool:
        try:
            self._make_request('GET', '/ping')
            return True
        except Exception:
            return False

    def get_itinerary_by_destination(self, destination: str) -> Dict:
        """Get itinerary weather for a destination"""
        return self._make_request(
            method='GET',
            endpoint=f'/api/itineraries/{destination}/template',
            params={'q': destination}
        )

    def update_itinerary(self, changes: Dict, itinerary_id: str, user_id: str) -> Dict:
        """Update itinerary with new details"""
        print(f"Updating itinerary for user {user_id} with changes: {changes}")
        return self._make_request(
            method='PUT',
            endpoint=f'/api/users/{user_id}/itineraries/{itinerary_id}',
            json=changes
        )