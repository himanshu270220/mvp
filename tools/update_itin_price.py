"This is a tool which takes in an itinerary object as argument and updates it with prices"
import requests
import json

def update_itinerary_price(itin: dict, uuid: str) -> dict:

    payload = {
        "itin": itin,
        "uuid": uuid
    }

    jarvis_endpoint = "some endpoint"

    headers = {
        "Content-Type":"application/json"
    }

    # Send p.ost request to jarvis which will return the itinerary object with prices updated
    try:
        jarvis_response = requests.post(url=jarvis_endpoint, data=json.dumps(payload), headers=headers)

        updated_itin = jarvis_response["itin"]

        return updated_itin
    
    except Exception as e:
        return f"Couldn't update itinerary: {e}"





