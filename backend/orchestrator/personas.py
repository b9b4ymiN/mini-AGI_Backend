"""
Persona management system for loading predefined system instructions.

Personas are stored as markdown files in backend/instruction/ directory.
"""

import os
from typing import Dict, Optional, List
from pathlib import Path


# Base directory for instruction files
INSTRUCTION_DIR = Path(__file__).parent.parent / "instruction"


# Persona registry mapping persona IDs to instruction filenames
PERSONA_REGISTRY: Dict[str, str] = {
    "oi-trader": "AI_System_Instructions_Trading_Analysis.md",
    # Add more personas here as you create instruction files
    # "example": "example_instructions.md",
}


def get_available_personas() -> List[Dict[str, str]]:
    """
    Get list of available personas with their metadata.

    Returns:
        List of dicts with persona info: [{"id": "oi-trader", "name": "OI Trader", "file": "..."}]
    """
    personas = []

    for persona_id, filename in PERSONA_REGISTRY.items():
        personas.append({
            "id": persona_id,
            "name": persona_id.replace("-", " ").title(),
            "file": filename,
            "exists": (INSTRUCTION_DIR / filename).exists()
        })

    return personas


def load_persona(persona_id: str) -> Optional[str]:
    """
    Load system instructions for a given persona.

    Args:
        persona_id: ID of the persona (e.g., "oi-trader")

    Returns:
        System instruction text, or None if persona not found

    Raises:
        FileNotFoundError: If persona file doesn't exist
        ValueError: If persona_id is not registered
    """
    # Normalize persona ID to lowercase
    persona_id = persona_id.lower().strip()

    # Check if persona is registered
    if persona_id not in PERSONA_REGISTRY:
        raise ValueError(
            f"Unknown persona: '{persona_id}'. "
            f"Available personas: {', '.join(PERSONA_REGISTRY.keys())}"
        )

    # Get filename
    filename = PERSONA_REGISTRY[persona_id]
    filepath = INSTRUCTION_DIR / filename

    # Check if file exists
    if not filepath.exists():
        raise FileNotFoundError(
            f"Persona instruction file not found: {filepath}\n"
            f"Expected location: {INSTRUCTION_DIR / filename}"
        )

    # Read and return content
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Strip leading/trailing whitespace
        return content.strip()

    except Exception as e:
        raise Exception(f"Failed to read persona file '{filename}': {e}")


def get_persona_or_custom(
    persona_id: Optional[str] = None,
    custom_instruction: Optional[str] = None
) -> str:
    """
    Get system instruction from persona or custom text (persona takes priority).

    Args:
        persona_id: Optional persona ID to load
        custom_instruction: Optional custom system instruction

    Returns:
        System instruction text (empty string if both are None)
    """
    # Persona takes priority over custom instruction
    if persona_id:
        try:
            return load_persona(persona_id)
        except (ValueError, FileNotFoundError) as e:
            # Log error but don't crash - fall back to custom or empty
            print(f"Warning: Failed to load persona '{persona_id}': {e}")
            return custom_instruction or ""

    return custom_instruction or ""
