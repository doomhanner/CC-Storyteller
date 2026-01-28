"""Tests for input parsing."""

import pytest

from storyteller.agents.archivist import ArchivistAgent
from storyteller.models.session import InputType


@pytest.fixture
def archivist():
    """Create an Archivist agent for testing."""
    return ArchivistAgent()


class TestInputParsing:
    """Test the input parsing functionality."""

    def test_plain_action(self, archivist):
        """Test parsing plain action text."""
        result = archivist.parse_input("I walk to the door")
        assert result.primary_type == InputType.ACTION
        assert result.action_text == "I walk to the door"
        assert result.dialogue_text is None
        assert result.thought_text is None

    def test_dialogue(self, archivist):
        """Test parsing dialogue."""
        result = archivist.parse_input('"Hello there!"')
        assert result.primary_type == InputType.DIALOGUE
        assert result.dialogue_text == "Hello there!"
        assert result.action_text is None or result.action_text == ""

    def test_thought(self, archivist):
        """Test parsing internal thoughts."""
        result = archivist.parse_input("*I wonder what she's thinking*")
        assert result.primary_type == InputType.THOUGHT
        assert result.thought_text == "I wonder what she's thinking"

    def test_ooc_command(self, archivist):
        """Test parsing OOC commands."""
        result = archivist.parse_input("((status))")
        assert result.primary_type == InputType.OOC
        assert result.ooc_command == "status"

    def test_continue_command(self, archivist):
        """Test parsing continue command."""
        result = archivist.parse_input("//")
        assert result.primary_type == InputType.CONTINUE

        result = archivist.parse_input("//continue")
        assert result.primary_type == InputType.CONTINUE

    def test_mixed_input(self, archivist):
        """Test parsing mixed input."""
        result = archivist.parse_input('I step forward. "Who goes there?" *hoping they\'re friendly*')
        assert result.primary_type == InputType.MIXED
        assert "step forward" in result.action_text
        assert result.dialogue_text == "Who goes there?"
        assert "hoping" in result.thought_text

    def test_multiple_dialogue(self, archivist):
        """Test parsing multiple dialogue quotes."""
        result = archivist.parse_input('"Hello" I pause. "Goodbye"')
        assert result.dialogue_text == "Hello Goodbye"

    def test_empty_input(self, archivist):
        """Test parsing empty input."""
        result = archivist.parse_input("")
        assert result.primary_type == InputType.ACTION
        assert result.action_text == "" or result.action_text is None
