"This is a tool which takes in a location as argument and sends a request to the crm for building a new itineray for that location"
import requests
import json

def scratch_itin_request(location: str, uuid: str):

    payload = {
        "location": location,
        "uuid": uuid,
        "type": "NewLocationRequest"
    }

    crm_endpoint = "some endpoint"

    headers = {
        "Content-Type":"application/json"
    }

    # Send post request to crm
    try:
        crm_response = requests.post(url=crm_endpoint, data=json.dumps(payload), headers=headers)

        if crm_response.status_code == "200":
            return "Request Sent"
        else:
            return f"Error from API: {crm_response.text}"
    
    except Exception as e:
        return f"Couldn't send request: {e}"