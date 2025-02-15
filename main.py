from agents.base_itinerary_agent import BaseItineraryAgent
from agents.itinerary_editor_agent import ItineraryEditorAgent
from flask import Flask, request, jsonify
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def chat(chat_request):
    """
    Process chat request using ManagerAgent and return response
    """
    try:
        print(chat_request['message'])
        print("session_id", chat_request['session_id'])
        message = chat_request['message']
        session_id = chat_request['session_id']
        intent = chat_request.get('intent', None)

        if not intent:
            return jsonify({
                'error': 'Missing intent in request'
            })
        thread = []

        if intent == 'base_itinerary':
            manager_agent = BaseItineraryAgent()
            thread = manager_agent.generate_response(session_id, message)

        elif intent == 'edit_itinerary':
            itinerary_editor_agent = ItineraryEditorAgent()
            thread = itinerary_editor_agent.generate_response(session_id, message)
        

        final_response = {
            'session_id': session_id,
            'message': thread
        }

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': final_response
        }
    except Exception as e:
        print(f'Error generating response: {str(e)}')
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }   

@app.route('/chat', methods=['POST', 'OPTIONS'])
def handle_chat():
    """
    Handle chat endpoint requests
    """
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return '', 204

    try:
        if not request.is_json:
            return jsonify({
                'error': 'Request must be JSON'
            }), 400

        body = request.get_json()
        
        # Validate required fields
        session_id = body.get('sessionID')
        msg_thread = body.get('msgThread')
        intent = body.get('intent')
        
        if not session_id or not msg_thread:
            return jsonify({
                'error': 'Missing required fields: sessionID and msgthread'
            }), 400
            
        chat_request = {
            'message': msg_thread,
            'session_id': session_id,
            'intent': intent
        }
        
        result = chat(chat_request)
        
        response_body = result.get('body', {})
        response_body_message = response_body.get('message', [])

        if response_body_message:
            last_message = response_body_message[-1]

            if last_message.get('type') == "json" and last_message.get('content'):
                try:
                    json_response = json.loads(last_message['content'])
                    response_body_message[-1]['content'] = json_response
                except json.JSONDecodeError as e:
                    print(f"JSON parsing error: {str(e)}")
                    pass

        return jsonify(response_body), result['statusCode'], result['headers']
        
    except json.JSONDecodeError:
        return jsonify({
            'error': 'Invalid JSON in request body'
        }), 400
        
    except Exception as e:
        print(f'Error processing request: {str(e)}')
        return jsonify({
            'error': f'Internal server error: {str(e)}'
        }), 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)