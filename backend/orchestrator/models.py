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


class ChatResponse(BaseModel):
    """Response with final answer and execution trace."""
    answer: str
    events: List[OrchestratorEvent]
