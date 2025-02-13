

from typing import Dict, List


def save_conversation(conversation: List[Dict[str, str]], file_path: str) -> None:
    """Save the conversation to a file"""
    
    with open(file_path, 'w') as file:
        for message in conversation:
            file.write(f"{message['user']}\n")
            file.write(f"{message['agent']}\n")
            file.write("\n")
    print(f"Conversation saved to {file_path}")