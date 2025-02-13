# Chatbot Project

## Setup Instructions

1. Create a virtual environment: 
    ```bash
    python3 -m venv venv
   ```
2. Activate the virtual environment:
   - On Windows:
   ```bash
   .\venv\Scripts\activate
   ```
   - On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```

3. Install required packages:
    ```bash
   pip install -r requirements.txt
   ```
4. Start the chatbot interface:
    ```bash
   python main.py
   ```
## Project Description
A simple chatbot interface built with Python.

## Requirements
- Python 3.x
- See requirements.txt for package dependencies

## Run redis queue
- docker run --name some-redis -p 6379:6379 -d redis