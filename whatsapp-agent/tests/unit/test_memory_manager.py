"""Unit tests for MemoryManager helper methods."""

from ai_companion.modules.memory.long_term.memory_manager import MemoryManager


def test_format_memories_empty():
    """format_memories_for_prompt should return empty string for empty list."""
    manager = MemoryManager.__new__(MemoryManager)
    result = manager.format_memories_for_prompt([])
    assert result == ""


def test_format_memories_single():
    """format_memories_for_prompt should format a single memory as a bullet."""
    manager = MemoryManager.__new__(MemoryManager)
    result = manager.format_memories_for_prompt(["User lives in Barcelona"])
    assert result == "- User lives in Barcelona"


def test_format_memories_multiple():
    """format_memories_for_prompt should format multiple memories as bullets."""
    manager = MemoryManager.__new__(MemoryManager)
    memories = ["User likes jazz", "User has a dog named Max"]
    result = manager.format_memories_for_prompt(memories)
    lines = result.split("\n")
    assert len(lines) == 2
    assert all(line.startswith("- ") for line in lines)
