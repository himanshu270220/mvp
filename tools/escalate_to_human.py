from enum import Enum
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass
import queue
import gradio as gr

class EscalationReason(Enum):
    COMPLEX_CODE_REVIEW = "Complex Code Review"
    SECURITY_CONCERN = "Security Concern"
    ARCHITECTURAL_DECISION = "Architectural Decision"
    BUSINESS_LOGIC = "Business Logic Clarification"
    TECHNICAL_LIMITATION = "Technical Limitation"
    OTHER = "Other"

@dataclass
class EscalationTicket:
    id: str
    user_id: str
    reason: EscalationReason
    description: str
    context: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None
    assigned_to: Optional[str] = None

class EscalationManager:
    def __init__(self):
        self.tickets: Dict[str, EscalationTicket] = {}
        self.ticket_queue = queue.Queue()
        self.current_ticket_id = 1
    
    def create_ticket(self, user_id: str, reason: EscalationReason, description: str, context: str) -> EscalationTicket:
        ticket_id = f"ESC-{self.current_ticket_id:04d}"
        self.current_ticket_id += 1
        
        ticket = EscalationTicket(
            id=ticket_id,
            user_id=user_id,
            reason=reason,
            description=description,
            context=context,
            status="PENDING",
            created_at=datetime.now()
        )
        
        self.tickets[ticket_id] = ticket
        self.ticket_queue.put(ticket_id)
        return ticket
    
    def resolve_ticket(self, ticket_id: str, resolution: str, resolved_by: str) -> Optional[EscalationTicket]:
        if ticket_id in self.tickets:
            ticket = self.tickets[ticket_id]
            ticket.status = "RESOLVED"
            ticket.resolution = resolution
            ticket.resolved_at = datetime.now()
            ticket.assigned_to = resolved_by
            return ticket
        return None
    
    def get_pending_tickets(self) -> List[EscalationTicket]:
        return [ticket for ticket in self.tickets.values() if ticket.status == "PENDING"]

class EscalationUI:
    def __init__(self, escalation_manager: EscalationManager):
        self.manager = escalation_manager
        
    def create_demo_interface(self) -> gr.Blocks:
        with gr.Blocks() as demo:
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Create Escalation")
                    reason = gr.Dropdown(
                        choices=[r.value for r in EscalationReason],
                        label="Reason for Escalation"
                    )
                    description = gr.Textbox(
                        label="Description",
                        placeholder="Describe the issue requiring escalation...",
                        lines=3
                    )
                    context = gr.Textbox(
                        label="Context",
                        placeholder="Provide any relevant context (code, error messages, etc.)",
                        lines=5
                    )
                    create_btn = gr.Button("Create Ticket", variant="primary")
                    status_msg = gr.Markdown(visible=False)
                
                with gr.Column(scale=1):
                    gr.Markdown("### Pending Tickets")
                    pending_tickets = gr.Dataframe(
                        headers=["Ticket ID", "Reason", "Description", "Created At"],
                        label="Pending Escalations"
                    )
                    refresh_btn = gr.Button("Refresh")
                    
                    with gr.Box():
                        gr.Markdown("### Resolve Ticket")
                        ticket_id = gr.Textbox(label="Ticket ID")
                        resolution = gr.Textbox(
                            label="Resolution",
                            placeholder="Provide resolution details...",
                            lines=3
                        )
                        resolver = gr.Textbox(label="Resolved By")
                        resolve_btn = gr.Button("Resolve Ticket")
                        resolve_status = gr.Markdown(visible=False)
            
            def create_ticket(reason, description, context):
                if not all([reason, description, context]):
                    return gr.update(visible=True, value="⚠️ Please fill in all fields")
                
                ticket = self.manager.create_ticket(
                    user_id="demo-user",
                    reason=EscalationReason(reason),
                    description=description,
                    context=context
                )
                return gr.update(visible=True, value=f"✅ Created ticket: {ticket.id}")
            
            def get_pending_tickets():
                tickets = self.manager.get_pending_tickets()
                return [[
                    t.id,
                    t.reason.value,
                    t.description,
                    t.created_at.strftime("%Y-%m-%d %H:%M:%S")
                ] for t in tickets]
            
            def resolve_ticket(ticket_id, resolution, resolver):
                if not all([ticket_id, resolution, resolver]):
                    return gr.update(visible=True, value="⚠️ Please fill in all fields")
                
                ticket = self.manager.resolve_ticket(ticket_id, resolution, resolver)
                if ticket:
                    return gr.update(visible=True, value=f"✅ Resolved ticket: {ticket_id}")
                return gr.update(visible=True, value="❌ Invalid ticket ID")
            
            create_btn.click(
                create_ticket,
                inputs=[reason, description, context],
                outputs=[status_msg]
            )
            
            refresh_btn.click(
                get_pending_tickets,
                outputs=[pending_tickets]
            )
            
            resolve_btn.click(
                resolve_ticket,
                inputs=[ticket_id, resolution, resolver],
                outputs=[resolve_status]
            )
            
        return demo

# Example usage and demo scenarios
def create_demo_scenarios(manager: EscalationManager):
    """Create some example escalation tickets for demonstration"""
    scenarios = [
        {
            "reason": EscalationReason.SECURITY_CONCERN,
            "description": "Potential security vulnerability in authentication flow",
            "context": """
            Found potential CSRF vulnerability in login endpoint.
            Current implementation doesn't validate origin of request.
            Need security expert review.
            """
        },
        {
            "reason": EscalationReason.COMPLEX_CODE_REVIEW,
            "description": "Complex optimization algorithm needs review",
            "context": """
            Implementing custom caching layer for high-traffic API endpoints.
            Need review of edge cases and potential race conditions.
            Current implementation: [code block]
            """
        },
        {
            "reason": EscalationReason.ARCHITECTURAL_DECISION,
            "description": "Database schema design for new microservice",
            "context": """
            Need to design schema for new user analytics service.
            Considering time-series vs document store approaches.
            Impact on existing services: [diagram]
            """
        }
    ]
    
    for scenario in scenarios:
        manager.create_ticket(
            user_id="demo-user",
            reason=scenario["reason"],
            description=scenario["description"],
            context=scenario["context"]
        )

if __name__ == "__main__":
    # Create manager and add demo scenarios
    manager = EscalationManager()
    create_demo_scenarios(manager)
    
    # Create and launch UI
    ui = EscalationUI(manager)
    demo = ui.create_demo_interface()
    demo.launch()