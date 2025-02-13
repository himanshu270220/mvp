import uuid
from agents.manage_agent import ManagerAgent
import gradio as gr
from typing import Any, List, Tuple
from dotenv import load_dotenv
import os
import sys

os.environ["OPIK_PROJECT_NAME"] = "Test"

if not (3, 10) <= sys.version_info < (3, 12):
    raise RuntimeError("This project requires Python >= 3.10 and < 3.12.")

class CustomStyles:
    """Class to manage custom CSS styles"""
    
    @staticmethod
    def get_css() -> str:
        return """
        .container {
            max-width: 1200px !important;
            margin: auto;
            padding: 20px;
        }
        .chatbot-container {
            height: 600px !important;
            overflow-y: auto;
        }
        .message-box {
            height: 100px !important;
            font-size: 16px !important;
        }
        """

class ChatbotHandler:
    """Class to handle chatbot functionality"""
    
    def __init__(self, user_id: str):
        self.manager_agent = ManagerAgent()
        self.user_id = user_id
    
    def process_message(self, user_input: str, chat_history: List[Tuple[str, str]], is_confirm: bool = False) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]], bool]:
        if not user_input.strip():
            return chat_history, chat_history, False
            
        if is_confirm:
            response = self.manager_agent.generate_response('pressed confirm button: finalize itinerary', self.user_id)
        else:
            response = self.manager_agent.generate_response(user_input, self.user_id)
        
        chat_history.append((user_input, response))
        show_confirm = True if "confirm button" in response.strip().lower() else False
        print("show confirm", show_confirm)
        return chat_history, chat_history, show_confirm

    def clear_chat(self) -> Tuple[str, List[Tuple[str, str]]]:
        """Clear chat history"""
        self.manager_agent.clear_conversation(self.user_id)
        return "", []

class UIComponents:
    """Class to manage UI components"""
    
    def __init__(self):
        self.chatbot = None
        self.message = None
        self.send_button = None
        self.clear_button = None
        self.chat_history = None
        self.confirm_button = None

    def create_header(self) -> gr.Markdown:
        """Create header component"""
        return gr.Markdown(
            """
            # AI Travel Assistant
            Welcome to your personal travel planning assistant. How can I help you today?
            """
        )

    def create_chat_interface(self) -> None:
        with gr.Row():
            with gr.Column(scale=12):
                self.chatbot = gr.Chatbot(
                    label="Conversation",
                    elem_classes="chatbot-container",
                    height=500,
                    show_label=False,
                )
                
                with gr.Row():
                    with gr.Column(scale=0.7):
                        self.message = gr.Textbox(
                            label="Your message",
                            placeholder="Type your message here...",
                            elem_classes="message-box",
                            show_label=False,
                        )
                    with gr.Column(scale=0.15):
                        self.send_button = gr.Button("Send", variant="primary", size="lg")
                    with gr.Column(scale=0.15):
                        self.confirm_button = gr.Button("Confirm", variant="secondary", size="lg", visible=False)

    def create_clear_button(self) -> None:
        """Create clear button component"""
        self.clear_button = gr.Button("Clear Conversation", size="sm")
        self.chat_history = gr.State([])

class TravelAssistant:
    """Main class for Travel Assistant application"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.ui = UIComponents()
        self.chatbot_handler = ChatbotHandler(user_id)
        self.styles = CustomStyles()

    def setup_event_handlers(self) -> None:
        msg_fn = self.chatbot_handler.process_message
        
        def update_ui(user_input, chat_history):
            result = msg_fn(user_input, chat_history)
            chat_history, _, show_confirm = result
            return chat_history, chat_history, gr.update(visible=show_confirm)

        def handle_confirm(chat_history):
            result = msg_fn("update itinerary", chat_history, True)
            return result[0], result[1], gr.update(visible=False)

        self.ui.message.submit(update_ui, [self.ui.message, self.ui.chat_history], 
                             [self.ui.chatbot, self.ui.chat_history, self.ui.confirm_button]
        ).then(lambda: "", None, self.ui.message)

        self.ui.send_button.click(update_ui, [self.ui.message, self.ui.chat_history],
                                [self.ui.chatbot, self.ui.chat_history, self.ui.confirm_button]
        ).then(lambda: "", None, self.ui.message)
        
        self.ui.confirm_button.click(handle_confirm, [self.ui.chat_history],
                                   [self.ui.chatbot, self.ui.chat_history, self.ui.confirm_button])
        
    def create_interface(self) -> gr.Blocks:
        """Create and return the complete interface"""
        with gr.Blocks(css=CustomStyles.get_css()) as demo:
            with gr.Column(elem_classes="container"):
                self.ui.create_header()
                self.ui.create_chat_interface()
                self.ui.create_clear_button()
                
                self.setup_event_handlers()
                
        return demo

def main(user_id: str):
    """Main function to initialize and launch the application"""
    load_dotenv()
    
    assistant = TravelAssistant(user_id)
    demo = assistant.create_interface()
    return demo

if __name__ == "__main__":

    test_user_id = str(uuid.uuid4()) # for testing purpose only
    demo = main(test_user_id)
    demo.launch()