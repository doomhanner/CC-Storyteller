"""
Chronicle - The CC-Storyteller GUI Application.

A terminal-based graphical interface for narrative simulation,
styled after ancient tomes and literary manuscripts.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from storyteller.gui.screens.home import HomeScreen
from storyteller.gui.screens.chronicle import ChronicleScreen
from storyteller.gui.screens.codex import CodexScreen
from storyteller.gui.screens.scriptorium import ScriptoriumScreen


class ChronicleApp(App):
    """
    The Chronicle - Main application for CC-Storyteller.

    Navigate the realms of your imagination through this ancient interface.
    """

    TITLE = "The Chronicle"
    SUB_TITLE = "A Narrative Simulation Engine"
    CSS_PATH = "styles/chronicle.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("h", "go_home", "Home", show=True),
        Binding("c", "open_codex", "Codex", show=True),
        Binding("n", "new_tale", "New Tale", show=True),
        Binding("?", "show_help", "Help", show=True),
        Binding("escape", "go_back", "Back", show=False),
    ]

    SCREENS = {
        "home": HomeScreen,
        "chronicle": ChronicleScreen,
        "codex": CodexScreen,
        "scriptorium": ScriptoriumScreen,
    }

    def __init__(self):
        super().__init__()
        self.current_campaign_id: str | None = None

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header(show_clock=True)
        yield Footer()

    def on_mount(self) -> None:
        """Handle application mount."""
        self.push_screen("home")

    def action_go_home(self) -> None:
        """Navigate to home screen."""
        self.switch_screen("home")

    def action_open_codex(self) -> None:
        """Open the Codex (Entity Bible)."""
        if self.current_campaign_id:
            self.push_screen(CodexScreen(self.current_campaign_id))
        else:
            self.notify("No campaign loaded. Select a campaign first.", severity="warning")

    def action_new_tale(self) -> None:
        """Start the campaign creation wizard."""
        self.push_screen("scriptorium")

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        if len(self.screen_stack) > 1:
            self.pop_screen()

    def action_show_help(self) -> None:
        """Show help screen."""
        self.notify(
            "Navigate with keys shown in footer.\n"
            "h=Home, c=Codex, n=New Tale, q=Quit",
            title="Help",
            timeout=5,
        )

    def load_campaign(self, campaign_id: str) -> None:
        """Load a campaign and switch to chronicle view."""
        self.current_campaign_id = campaign_id
        self.push_screen(ChronicleScreen(campaign_id))


def run() -> None:
    """Run the Chronicle application."""
    app = ChronicleApp()
    app.run()


if __name__ == "__main__":
    run()
