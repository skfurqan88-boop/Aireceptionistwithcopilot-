"""
AI Conversation Layer

This module implements the AI interface for appointment booking.
The AI ONLY handles conversation - it NEVER makes booking decisions.

ENFORCEMENT RULES:
1. Always call availability/check before offering any time
2. Never assume availability
3. If slot is locked, offer nearest available slots
4. Never say "booked" until confirm API succeeds
"""

import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from openai import AzureOpenAI
import json


class AIReceptionist:
    """
    AI Receptionist for conversation handling.
    
    This class manages the conversation flow but delegates all
    booking logic to the backend APIs.
    """
    
    def __init__(self):
        """Initialize Azure OpenAI client"""
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-01",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        
        # System prompt enforces strict rules
        self.system_prompt = """You are an AI Receptionist for appointment booking.

CRITICAL RULES (NEVER VIOLATE):
1. You ONLY handle conversation - you do NOT decide availability
2. You MUST call the check_availability function before offering ANY time slot
3. You NEVER confirm a booking until the confirm_appointment function succeeds
4. If a slot is not available, offer the suggested alternative slots
5. Always be polite and professional
6. Collect: customer name, phone number, preferred date/time, service type
7. Never assume - always confirm details with the customer

CONVERSATION FLOW:
1. Greet and ask what service they need
2. Ask for preferred date and time
3. Call check_availability - if available, inform them the slot is temporarily held
4. Ask for their name and phone number
5. Call confirm_appointment - only then say "booking confirmed"
6. Provide confirmation details

Remember: You are the interface, the system is the authority."""
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        available_functions: Dict
    ) -> Tuple[str, Optional[Dict]]:
        """
        Process a chat message and return response.
        
        Args:
            messages: Conversation history
            available_functions: Dictionary of function definitions
        
        Returns:
            Tuple of (response_text, function_call_info)
        """
        # Add system prompt
        full_messages = [{"role": "system", "content": self.system_prompt}] + messages
        
        # Define function schemas for the API
        functions = [
            {
                "name": "check_availability",
                "description": "Check if a requested time slot is available. MUST be called before offering any time to customer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "business_id": {
                            "type": "string",
                            "description": "The business ID"
                        },
                        "requested_datetime": {
                            "type": "string",
                            "description": "Requested datetime in ISO format"
                        },
                        "service_type": {
                            "type": "string",
                            "description": "Type of service"
                        },
                        "customer_phone": {
                            "type": "string",
                            "description": "Customer phone number if already collected"
                        }
                    },
                    "required": ["business_id", "requested_datetime", "service_type"]
                }
            },
            {
                "name": "confirm_appointment",
                "description": "Confirm the appointment booking. ONLY call this after customer confirms all details.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "business_id": {
                            "type": "string",
                            "description": "The business ID"
                        },
                        "lock_id": {
                            "type": "string",
                            "description": "Lock ID from availability check"
                        },
                        "customer_name": {
                            "type": "string",
                            "description": "Customer full name"
                        },
                        "customer_phone": {
                            "type": "string",
                            "description": "Customer phone number"
                        },
                        "service_type": {
                            "type": "string",
                            "description": "Type of service"
                        }
                    },
                    "required": ["business_id", "lock_id", "customer_name", "customer_phone", "service_type"]
                }
            },
            {
                "name": "cancel_appointment",
                "description": "Cancel an existing appointment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "appointment_id": {
                            "type": "string",
                            "description": "The appointment ID to cancel"
                        },
                        "customer_phone": {
                            "type": "string",
                            "description": "Customer phone for verification"
                        }
                    },
                    "required": ["appointment_id", "customer_phone"]
                }
            }
        ]
        
        # Call Azure OpenAI
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=full_messages,
            functions=functions,
            function_call="auto"
        )
        
        message = response.choices[0].message
        
        # Check if function call is requested
        if message.function_call:
            function_name = message.function_call.name
            function_args = json.loads(message.function_call.arguments)
            
            return "", {
                "name": function_name,
                "arguments": function_args
            }
        else:
            return message.content, None
    
    def format_availability_response(
        self,
        status: str,
        lock_id: Optional[str],
        expires_at: Optional[str],
        suggested_slots: List[str],
        reason: Optional[str]
    ) -> str:
        """
        Format availability check response for the AI.
        
        This tells the AI what to communicate to the customer.
        """
        if status == "AVAILABLE":
            return f"SLOT_AVAILABLE: The time slot is available and has been temporarily held for 3 minutes (lock_id: {lock_id}). Inform the customer and collect their details to confirm."
        elif status == "TEMP_LOCKED":
            if suggested_slots:
                slots_formatted = ", ".join(suggested_slots[:3])
                return f"SLOT_TEMPORARILY_LOCKED: This slot is being held by another customer. Suggest these available alternatives: {slots_formatted}"
            else:
                return "SLOT_TEMPORARILY_LOCKED: This slot is being held by another customer. Please suggest a different time or ask for their preferred date range."
        else:
            if suggested_slots:
                slots_formatted = ", ".join(suggested_slots[:3])
                return f"SLOT_NOT_AVAILABLE ({reason}): Offer these available alternatives: {slots_formatted}"
            else:
                return f"SLOT_NOT_AVAILABLE ({reason}): No slots available. Ask customer for different date/time preferences."
    
    def format_confirmation_response(
        self,
        success: bool,
        appointment_id: Optional[str],
        start_datetime: Optional[str],
        reason: Optional[str]
    ) -> str:
        """
        Format appointment confirmation response for the AI.
        """
        if success:
            return f"BOOKING_CONFIRMED: Appointment {appointment_id} confirmed for {start_datetime}. Inform customer their booking is complete and provide confirmation details."
        else:
            return f"BOOKING_FAILED ({reason}): The booking could not be completed. Apologize and offer to help find another time."


# Conversation state management
class ConversationManager:
    """
    Manages conversation state for each customer session.
    """
    
    def __init__(self):
        self.sessions: Dict[str, List[Dict]] = {}
    
    def get_session(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the conversation history"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append({"role": role, "content": content})
    
    def clear_session(self, session_id: str):
        """Clear a conversation session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
