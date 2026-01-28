"""
Chronicle Screen - The Narrative Canvas.

The main gameplay screen where the story unfolds.
"""

import asyncio

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Markdown, Static
from textual.worker import Worker, WorkerState

from storyteller.session.session_manager import SessionManager


class NarrativeEntry(Static):
    """A single narrative entry in the chronicle."""

    def __init__(
        self,
        content: str,
        entry_type: str = "narrative",
        turn_number: int | None = None,
    ) -> None:
        super().__init__()
        self.content = content
        self.entry_type = entry_type
        self.turn_number = turn_number

    def compose(self) -> ComposeResult:
        """Compose the narrative entry."""
        if self.entry_type == "player":
            yield Static(
                f"[bold green]> {self.content}[/bold green]",
                classes="player-input",
            )
        elif self.entry_type == "ooc":
            yield Static(self.content, classes="ooc-response")
        else:
            yield Markdown(self.content, classes="narrative-text")
            if self.turn_number:
                yield Static(
                    f"{{T: {self.turn_number}}}",
                    classes="narrative-turn-tag",
                )


class StatusBar(Static):
    """Status bar showing current game state."""

    def __init__(self, manager: SessionManager) -> None:
        super().__init__()
        self.manager = manager

    def compose(self) -> ComposeResult:
        """Compose the status bar."""
        ws = self.manager.world_state

        location = "Unknown"
        if ws.current_location:
            location = ws.current_location.name

        time = ws.game_time or "???"
        turn = self.manager.current_turn

        yield Static(f"📍 {location}", classes="status-item")
        yield Static(f"🕐 {time}", classes="status-item")
        yield Static(f"📜 Turn {turn}", classes="status-item")

        # PC status
        if ws.pc_status.conditions:
            conditions = ", ".join(ws.pc_status.conditions[:2])
            yield Static(f"⚠️ {conditions}", classes="status-item")


class ChronicleScreen(Screen):
    """
    The Chronicle - Main gameplay screen.

    Where the narrative unfolds and the player interacts with the world.
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("ctrl+s", "save_game", "Save"),
        ("ctrl+c", "open_codex", "Codex"),
    ]

    def __init__(self, campaign_id: str) -> None:
        super().__init__()
        self.campaign_id = campaign_id
        self.manager: SessionManager | None = None
        self._processing = False

    def compose(self) -> ComposeResult:
        """Compose the chronicle screen layout."""
        with Container(id="chronicle-container"):
            yield ScrollableContainer(id="narrative-scroll")

            with Horizontal(id="status-bar"):
                yield Static("Loading...", classes="status-item")

            with Container(id="input-area"):
                yield Input(
                    placeholder="Enter your action, dialogue, or command...",
                    id="player-input",
                )

    def on_mount(self) -> None:
        """Initialize the session when screen mounts."""
        self.load_session()

    def load_session(self) -> None:
        """Load the campaign session."""
        try:
            self.manager = SessionManager.load(self.campaign_id)

            # Display opening or recap
            opening = self.manager.start_session()
            self.add_narrative(opening, turn_number=self.manager.current_turn or 1)

            # Update status bar
            self.update_status_bar()

            # Focus the input
            self.query_one("#player-input", Input).focus()

        except Exception as e:
            self.notify(f"Failed to load campaign: {e}", severity="error")
            self.app.pop_screen()

    def update_status_bar(self) -> None:
        """Update the status bar with current state."""
        if not self.manager:
            return

        status_bar = self.query_one("#status-bar", Horizontal)
        status_bar.remove_children()

        ws = self.manager.world_state

        location = "Unknown"
        if ws.current_location:
            location = ws.current_location.name

        time = ws.game_time or "???"
        turn = self.manager.current_turn

        status_bar.mount(Static(f"📍 {location}", classes="status-item"))
        status_bar.mount(Static(f"🕐 {time}", classes="status-item"))
        status_bar.mount(Static(f"📜 Turn {turn}", classes="status-item"))

        if ws.pc_status.conditions:
            conditions = ", ".join(ws.pc_status.conditions[:2])
            status_bar.mount(Static(f"⚠️ {conditions}", classes="status-item"))

    def add_narrative(
        self,
        content: str,
        entry_type: str = "narrative",
        turn_number: int | None = None,
    ) -> None:
        """Add a narrative entry to the scroll."""
        scroll = self.query_one("#narrative-scroll", ScrollableContainer)
        entry = NarrativeEntry(content, entry_type, turn_number)
        scroll.mount(entry)
        scroll.scroll_end(animate=False)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle player input submission."""
        if self._processing or not self.manager:
            return

        player_input = event.value.strip()
        if not player_input:
            return

        # Clear input
        event.input.value = ""

        # Check for quit
        if player_input.lower() in ["quit", "exit", "((quit))"]:
            self.manager.save()
            self.notify("Chronicle saved.", severity="information")
            self.app.pop_screen()
            return

        # Show player input
        self.add_narrative(player_input, entry_type="player")

        # Process turn
        self._processing = True
        self.query_one("#player-input", Input).disabled = True

        # Show loading indicator
        self.add_narrative("_The chronicle is being written..._", entry_type="loading")

        # Run in worker thread
        self.run_worker(self.process_turn_async(player_input), exclusive=True)

    async def process_turn_async(self, player_input: str) -> None:
        """Process the turn asynchronously."""
        try:
            result = await self.manager.process_turn(player_input)

            # Remove loading indicator
            scroll = self.query_one("#narrative-scroll", ScrollableContainer)
            children = list(scroll.children)
            if children:
                # Remove the last entry if it's the loading indicator
                last = children[-1]
                if isinstance(last, NarrativeEntry) and last.entry_type == "loading":
                    last.remove()

            # Determine entry type
            entry_type = "ooc" if result.narrative.startswith("[OOC]") else "narrative"

            # Add narrative
            self.add_narrative(
                result.narrative,
                entry_type=entry_type,
                turn_number=result.turn_number if entry_type == "narrative" else None,
            )

            # Update status
            self.update_status_bar()

        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        finally:
            self._processing = False
            input_widget = self.query_one("#player-input", Input)
            input_widget.disabled = False
            input_widget.focus()

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        if event.state == WorkerState.ERROR:
            self.notify("An error occurred processing your input", severity="error")
            self._processing = False
            self.query_one("#player-input", Input).disabled = False

    def action_go_back(self) -> None:
        """Go back to home screen."""
        if self.manager:
            self.manager.save()
            self.notify("Chronicle saved.", severity="information")
        self.app.pop_screen()

    def action_save_game(self) -> None:
        """Save the current game state."""
        if self.manager:
            self.manager.save()
            self.notify("Chronicle saved.", severity="information")

    def action_open_codex(self) -> None:
        """Open the Codex for this campaign."""
        from storyteller.gui.screens.codex import CodexScreen
        self.app.push_screen(CodexScreen(self.campaign_id))
