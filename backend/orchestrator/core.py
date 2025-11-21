"""
Main orchestration loop for coordinating agents and tools.
"""

from typing import Tuple, List, Optional
import json
from .models import OrchestratorEvent
from .agents import run_agent, AGENTS
from .tools import TOOLS
from . import memory


def orchestrate(
    user_input: str,
    max_steps: int = 10,
    system_instruction: str = "",
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    persona: Optional[str] = None
) -> Tuple[str, List[OrchestratorEvent], str, bool]:
    """
    Main orchestration loop with conversation memory.

    Args:
        user_input: User's query or instruction
        max_steps: Maximum orchestration steps (default: 10)
        system_instruction: Optional custom system instruction to prepend to all agents
        session_id: Optional session ID for conversation continuity
        user_id: Optional user ID for personalization
        persona: Optional persona used

    Returns:
        Tuple of (final_answer, event_list, session_id, context_used)
    """
    # Get or create session
    session_id = memory.get_or_create_session(session_id, user_id)

    # Retrieve conversation context
    conversation_context = memory.get_recent_context(session_id, max_turns=5, max_chars=2000)

    # Retrieve user facts (long-term memory)
    user_facts = memory.format_memory_facts(user_id) if user_id else ""

    # Combine all context
    full_context = []
    if user_facts:
        full_context.append(user_facts)
    if conversation_context:
        full_context.append(conversation_context)

    context_used = bool(full_context)

    # Initialize state
    context_log: List[str] = []
    if full_context:
        context_log.append("\n\n".join(full_context))

    events: List[OrchestratorEvent] = []
    current_agent: str = "orchestrator"
    current_query: str = user_input

    # Main loop
    for step in range(max_steps):
        # 1. Execute current agent
        result = run_agent(
            current_agent,
            current_query,
            extra_context="\n".join(context_log),
            custom_system_instruction=system_instruction
        )

        # 2. Extract fields
        thought = result.get("thought", "")
        action = result.get("action", "final")
        tool_name = result.get("tool")
        target_agent = result.get("target_agent")
        args = result.get("args", {}) or {}
        answer = result.get("answer", "")

        # 3. Record event
        events.append(
            OrchestratorEvent(
                step=step + 1,
                agent=current_agent,
                action=action,
                tool=tool_name,
                target_agent=target_agent,
                thought=thought,
            )
        )

        # 4. Update context log
        context_log.append(
            f"[{current_agent} step {step+1}] {json.dumps(result, ensure_ascii=False)}"
        )

        # 5. Handle action
        if action == "final":
            # Done - save conversation and return answer
            final_answer = answer or "[NO ANSWER]"
            memory.save_conversation(
                session_id=session_id,
                user_message=user_input,
                ai_response=final_answer,
                user_id=user_id,
                persona=persona
            )
            return (final_answer, events, session_id, context_used)

        elif action == "use_tool":
            # Execute tool
            if tool_name and tool_name in TOOLS:
                tool_fn = TOOLS[tool_name]
                tool_output = tool_fn(**args)

                # Prepare next query with tool result
                current_query = (
                    f"Tool `{tool_name}` output:\n{tool_output}\n\n"
                    "Now continue your reasoning and decide next action."
                )
                # Stay with same agent
            else:
                # Unknown tool - ask agent to provide final answer
                current_agent = "orchestrator"
                current_query = (
                    f"Unknown tool '{tool_name}'. "
                    "Please provide a final answer with available information."
                )

        elif action == "delegate":
            # Switch to target agent
            if target_agent and target_agent in AGENTS:
                current_agent = target_agent
                current_query = args.get("task", answer) or f"User goal: {user_input}"
            else:
                # Unknown agent - reset to orchestrator
                current_agent = "orchestrator"
                current_query = (
                    f"Unknown agent '{target_agent}'. "
                    "Please handle the task yourself or use available tools."
                )

        else:
            # Invalid action - ask for final
            current_agent = "orchestrator"
            current_query = (
                f"Invalid action '{action}'. "
                f"Previous JSON: {json.dumps(result)}\n"
                "Please provide a 'final' answer."
            )

    # Max steps reached without final
    final_answer = "[MAX STEPS REACHED - No final answer provided]"
    memory.save_conversation(
        session_id=session_id,
        user_message=user_input,
        ai_response=final_answer,
        user_id=user_id,
        persona=persona
    )
    return (final_answer, events, session_id, context_used)
