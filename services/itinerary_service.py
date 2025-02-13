import copy
import datetime
from requests import request
from flask import Flask, jsonify, abort
from typing import Dict, Any, Optional

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from tools.redis_cache import RedisCache


app = Flask(__name__)

class ItineraryService:
    def __init__(self):
        self.template_itineraries = {
            "dubai": {
                "itinerary_id": "123",
                "packageName": "Dubai Standard Package",
                "rating": 4.8,
                "duration": "4 Nights & 5 Days",
                "inclusions": {
                    "airfare": "Return Economy Airfare",
                    "accommodation": "4-star hotel for 4 nights",
                    "meals": "4 breakfasts at the hotel",
                    "transportation": {
                        "airportTransfers": "Return private airport transfers",
                        "cityTour": "Half Day Dubai City Tour with shared transfer",
                        "desertSafari": "Standard Desert Safari with shared transfer (Falcon Camp or Similar)",
                        "burjKhalifa": "At the Top Burj Khalifa (124 & 125 Floors - Non Prime Time) with shared transfer",
                        "creekCruise": "Dubai Creek Cruise with shared transfer"
                    },
                    "insurance": "Travel Insurance",
                    "taxes": "GST and TCS"
                },
                "itinerary": [
                    {
                        "day": 1,
                        "title": "Arrival in Dubai",
                        "description": "Meet and greet at the airport, transfer to the hotel (standard check-in time is 3 PM). Day at leisure. Overnight at the hotel."
                    },
                    {
                        "day": 2,
                        "title": "Dubai City Tour and Desert Safari",
                        "description": "Buffet breakfast at the hotel. Half-day Dubai City Tour with return shared transfer. Standard Desert Safari with return shared transfer. Overnight at the hotel."
                    },
                    {
                        "day": 3,
                        "title": "Dubai Creek Cruise and Burj Khalifa",
                        "description": "Buffet breakfast at the hotel. Dubai Creek Cruise with shared transfer. Visit 'At the Top Burj Khalifa' (124 & 125 Floors - Non Prime Time) with return shared transfer. Overnight at the hotel."
                    },
                    {
                        "day": 4,
                        "title": "Free Day for Exploration",
                        "description": "Buffet breakfast at the hotel. The day is free for you to customize as per your interest. Holiday Tribe can assist with planning if needed. Overnight at the hotel."
                    },
                    {
                        "day": 5,
                        "title": "Departure from Dubai",
                        "description": "Buffet breakfast at the hotel. Departure transfer to Dubai airport. Return flight back to India."
                    }
                ],
                "exclusions": [
                    "Visa cost",
                    "Seat selection and meals cost on low-cost carriers",
                    "Sightseeing not mentioned in the itinerary",
                    "Meals other than mentioned",
                    "Early check-in at the hotel",
                    "Local taxes (if any)",
                    "Tips and gratuities",
                    "Anything else not mentioned in the inclusions"
                ],
                "contactDetails": {
                    "phone": "+91-9205553343",
                    "email": "contact@holidaytribe.com",
                    "social": "@holidaytribeworld"
                }
            },
            "bali": {
                "packageName": "Bali Explorer Package",
                "rating": 4.7,
                "duration": "5 Nights & 6 Days",
                "inclusions": {
                    "airfare": "Return Economy Airfare",
                    "accommodation": "4-star villa stay for 5 nights",
                    "meals": "Daily breakfast and 2 dinners",
                    "transportation": {
                        "airportTransfers": "Private airport transfers",
                        "ubudTour": "Full-day Ubud tour with private driver",
                        "templeVisit": "Tanah Lot Temple sunset tour",
                        "waterSports": "Water sports package at Nusa Dua",
                        "spaDay": "Traditional Balinese massage"
                    },
                    "insurance": "Travel Insurance",
                    "taxes": "All applicable taxes"
                },
                "itinerary": [
                    {
                        "day": 1,
                        "title": "Welcome to Bali",
                        "description": "Arrival at Denpasar Airport, transfer to your villa in Seminyak. Welcome dinner at a local restaurant. Overnight at villa."
                    },
                    {
                        "day": 2,
                        "title": "Ubud Cultural Tour",
                        "description": "Full-day tour of Ubud, visiting art galleries, Monkey Forest, and rice terraces. Traditional dance performance in evening."
                    },
                    {
                        "day": 3,
                        "title": "Beach and Water Sports",
                        "description": "Water sports activities at Nusa Dua beach. Afternoon at leisure. Sunset visit to Tanah Lot Temple."
                    },
                    {
                        "day": 4,
                        "title": "Spa and Relaxation",
                        "description": "Morning yoga session. Traditional Balinese massage. Free afternoon for shopping or beach time."
                    },
                    {
                        "day": 5,
                        "title": "Free Day",
                        "description": "Free day to explore on your own. Optional tours available. Farewell dinner at beachfront restaurant."
                    },
                    {
                        "day": 6,
                        "title": "Departure",
                        "description": "Breakfast at villa. Transfer to airport for return flight."
                    }
                ],
                "exclusions": [
                    "Visa on arrival fee",
                    "Personal expenses",
                    "Additional activities",
                    "Tips for drivers and guides",
                    "Meals not mentioned",
                    "Mini bar consumption"
                ],
                "contactDetails": {
                    "phone": "+91-9205553343",
                    "email": "contact@holidaytribe.com",
                    "social": "@holidaytribeworld"
                }
            }
        }

    def get_template_itinerary(self, destination: str) -> Optional[Dict[str, Any]]:
        """Get the template itinerary for a destination"""
        return self.template_itineraries.get(destination.lower())

    def get_itinerary(self, destination: str) -> Optional[Dict[str, Any]]:
        """Get user's personalized itinerary for a destination"""
        itinerary = self.template_itineraries.get(destination, {})
        return itinerary

    
    def create_user_itinerary(self, destination: str) -> Optional[Dict[str, Any]]:
        """Create a new user-specific itinerary from template"""
        template = self.get_template_itinerary(destination.lower())
        if not template:
            return None
        return template

    def update_user_itinerary(
        self, 
        user_id: str,
        itinerary_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a user's personalized itinerary"""
        # Get existing user itinerary or create new one
        cache = RedisCache()
        user_itinerary = cache.get_itinerary(user_id + '-' + itinerary_id)
        updated_itinerary = copy.deepcopy(user_itinerary)

        # Handle duration change
        if 'duration_days' in updates:
            new_days = updates['duration_days']
            new_nights = new_days - 1
            updated_itinerary['duration'] = f"{new_nights} Nights & {new_days} Days"
            
            # Update accommodation
            updated_itinerary['inclusions']['accommodation'] = \
                updated_itinerary['inclusions']['accommodation'].replace(
                    str(len(user_itinerary['itinerary']) - 1),
                    str(new_nights)
                )
            
            # Adjust itinerary days
            current_days = len(user_itinerary['itinerary'])
            if new_days > current_days:
                # Add free days before departure
                last_day = updated_itinerary['itinerary'].pop()
                for day in range(current_days, new_days):
                    updated_itinerary['itinerary'].append({
                        "day": day,
                        "title": "Free Day for Exploration",
                        "description": "Buffet breakfast at the hotel. Day at leisure for optional activities or relaxation. Overnight at the hotel."
                    })
                updated_itinerary['itinerary'].append(last_day)
            elif new_days < current_days:
                # Preserve essential days
                essential_days = [updated_itinerary['itinerary'][0]]
                important_days = []
                
                for day in updated_itinerary['itinerary'][1:-1]:
                    if not "Free Day" in day['title']:
                        important_days.append(day)
                
                essential_days.extend(important_days[:new_days-2])
                essential_days.append(updated_itinerary['itinerary'][-1])
                
                # Update day numbers
                for i, day in enumerate(essential_days, 1):
                    day['day'] = i
                
                updated_itinerary['itinerary'] = essential_days

        # Handle new activities
        if 'add_activities' in updates:
            for activity in updates['add_activities']:
                day_num = activity.get('day', None)
                if day_num and 1 <= day_num <= len(updated_itinerary['itinerary']):
                    day = updated_itinerary['itinerary'][day_num - 1]
                    if "Free Day" in day['title']:
                        day['title'] = activity['title']
                    day['description'] = day['description'].replace(
                        "Day at leisure",
                        activity['description']
                    )
                    
                    if activity.get('inclusion_key'):
                        updated_itinerary['inclusions']['transportation'][activity['inclusion_key']] = \
                            activity['description']

        # Handle activity removals
        if 'remove_activities' in updates:
            for activity_name in updates['remove_activities']:
                # Remove from inclusions
                if 'transportation' in updated_itinerary['inclusions']:
                    updated_itinerary['inclusions']['transportation'] = {
                        k: v for k, v in updated_itinerary['inclusions']['transportation'].items()
                        if activity_name.lower() not in v.lower()
                    }
                
                # Update daily itinerary
                for day in updated_itinerary['itinerary']:
                    if activity_name.lower() in day['description'].lower():
                        day['description'] = "Buffet breakfast at the hotel. Day at leisure. Overnight at the hotel."
                        if "Free Day" not in day['title']:
                            day['title'] = "Free Day for Exploration"

        # Update metadata
        updated_itinerary['metadata']['last_modified'] = datetime.now().isoformat()
        updated_itinerary['metadata']['version'] += 1

        # Store updated itinerary
        cache.set_itinerary(user_id + '-' + itinerary_id, updated_itinerary)
        return updated_itinerary



# Initialize the service
itinerary_service = ItineraryService()

@app.route('/api/itineraries/<destination>/template', methods=['GET'])
def get_template_itinerary(destination):
    """Get the template itinerary for a destination"""
    itinerary = itinerary_service.get_template_itinerary(destination)
    if itinerary is None:
        abort(404, description=f"No template found for destination: {destination}")
    return jsonify(itinerary)

@app.route('/api/users/itineraries/<destination>', methods=['GET'])
def get_user_itinerary(destination):
    """Get user's personalized itinerary"""
    itinerary = itinerary_service.get_user_itinerary(destination)
    return jsonify(itinerary)

@app.route('/api/users/<user_id>/itineraries/<itinerary_id>', methods=['PUT'])
def update_user_itinerary(user_id: str, itinerary_id: str):
    """Update user's personalized itinerary"""
    if not request.is_json:
        abort(400, description="Request must be JSON")
        
    updates = request.json
    updated_itinerary = itinerary_service.update_user_itinerary(user_id, itinerary_id, updates)
    
    if updated_itinerary is None:
        abort(404, description=f"Could not update itinerary for user id: {user_id} and itinerary id: {itinerary_id}")
        
    return jsonify(updated_itinerary)

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": str(error.description)}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)