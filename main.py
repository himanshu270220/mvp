from flask import Flask, request, jsonify
import json
from agents.manage_agent import ManagerAgent
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
        
        manager_agent = ManagerAgent()
        thread = manager_agent.generate_response(session_id, message)

        chat_request['message'] = thread

        final_response = {
            'session_id': session_id,
            'message': chat_request['message']
        }

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps(final_response)
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
        
        if not session_id or not msg_thread:
            return jsonify({
                'error': 'Missing required fields: sessionID and msgthread'
            }), 400
            
        chat_request = {
            'message': msg_thread,
            'session_id': session_id
        }
        
        result = chat(chat_request)
        
        # Extract response from chat result
        response_body = json.loads(result['body'])
        
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