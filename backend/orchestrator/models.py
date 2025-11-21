"""
Pydantic models for API requests, responses, and orchestration events.
"""

from pydantic import BaseModel
from typing import List, Optional, Any, Dict


class OrchestratorEvent(BaseModel):
    """Record of a single orchestration step."""
    step: int
    agent: str
    action: str
    tool: Optional[str] = None
    target_agent: Optional[str] = None
    thought: str


class ChatRequest(BaseModel):
    """Request format matching assistant-ui."""
    messages: List[Dict[str, Any]]
    persona: Optional[str] = None  # Optional persona ID (e.g., "oi-trader")
    session_id: Optional[str] = None  # Optional session ID for conversation memory
    user_id: Optional[str] = None  # Optional user ID for personalization


class ChatResponse(BaseModel):
    """Response with final answer and execution trace."""
    answer: str
    events: List[OrchestratorEvent]
    session_id: Optional[str] = None  # Session ID for continued conversation
    context_used: Optional[bool] = False  # Whether conversation context was used
