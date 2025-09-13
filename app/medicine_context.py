"""
Medicine context data for OpenAI Realtime conversations.
Provides static medicine information for the AI assistant.
"""
from typing import Dict, Any


# Default medicine context used by the AI assistant
MEDICINE_CONTEXT: Dict[str, Any] = {
    "name": "paracetamol",
    "form": "tablet", 
    "route": "oral",
    "meal_configuration": "after meal",
    "time": "08:00",
    "dosage_value": 500,
    "dosage_unit": "mg"
}

# System prompt for OpenAI Realtime API
SYSTEM_PROMPT = """You are a friendly, concise medication reminder assistant. Use the provided 'medicine' JSON to answer patient questions. Always prioritize safety: do not provide medical advice beyond the medication label. If asked about dose or timing, repeat the provided official values. If user expresses severe symptoms, instruct them to seek urgent care."""

# Initial greeting message that AI speaks first
INITIAL_GREETING = "It's time to take your medicine"


def get_medicine_context() -> Dict[str, Any]:
    """Get the current medicine context."""
    return MEDICINE_CONTEXT.copy()


def get_system_prompt() -> str:
    """Get the system prompt for OpenAI Realtime API."""
    return SYSTEM_PROMPT


def get_initial_greeting() -> str:
    """Get the initial greeting message."""
    return INITIAL_GREETING


def format_medicine_info() -> str:
    """Format medicine information for AI context."""
    medicine = get_medicine_context()
    return f"""Medicine Information:
- Name: {medicine['name']}
- Form: {medicine['form']}
- Route: {medicine['route']}
- Timing: {medicine['time']} {medicine['meal_configuration']}
- Dosage: {medicine['dosage_value']}{medicine['dosage_unit']}"""