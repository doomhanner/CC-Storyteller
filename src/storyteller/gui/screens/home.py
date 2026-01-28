"""
Home Screen - The Hall of Chronicles.

The main menu showing available campaigns and actions.
"""

import json

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Label, ListItem, ListView, Static

from storyteller.config import get_settings

# ASCII art title
TITLE_ART = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     ████████╗██╗  ██╗███████╗                                ║
║     ╚══██╔══╝██║  ██║██╔════╝                                ║
║        ██║   ███████║█████╗                                  ║
║        ██║   ██╔══██║██╔══╝                                  ║
║        ██║   ██║  ██║███████╗                                ║
║        ╚═╝   ╚═╝  ╚═╝╚══════╝                                ║
║                                                               ║
║      ██████╗██╗  ██╗██████╗  ██████╗ ███╗   ██╗██╗ ██████╗██╗    ███████╗ ║
║     ██╔════╝██║  ██║██╔══██╗██╔═══██╗████╗  ██║██║██╔════╝██║    ██╔════╝ ║
║     ██║     ███████║██████╔╝██║   ██║██╔██╗ ██║██║██║     ██║    █████╗   ║
║     ██║     ██╔══██║██╔══██╗██║   ██║██║╚██╗██║██║██║     ██║    ██╔══╝   ║
║     ╚██████╗██║  ██║██║  ██║╚██████╔╝██║ ╚████║██║╚██████╗███████╗███████╗║
║      ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝ ╚═════╝╚══════╝╚══════╝║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""

SIMPLE_TITLE = """
╔═══════════════════════════════════════╗
║         T H E   C H R O N I C L E     ║
║     A Narrative Simulation Engine     ║
╚═══════════════════════════════════════╝
"""


class CampaignListItem(ListItem):
    """A campaign entry in the list."""

    def __init__(self, campaign_data: dict) -> None:
        super().__init__()
        self.campaign_data = campaign_data

    def compose(self) -> ComposeResult:
        """Compose the campaign item."""
        data = self.campaign_data
        status_color = {
            "draft": "yellow",
            "ready": "green",
            "active": "cyan",
            "paused": "orange",
            "completed": "blue",
        }.get(data.get("status", ""), "white")

        yield Static(
            f"[bold]{data.get('name', 'Unnamed')}[/bold]\n"
            f"[dim]Turn {data.get('turn', 0)} • {data.get('sessions', 0)} sessions[/dim]\n"
            f"[{status_color}]● {data.get('status', 'unknown').title()}[/{status_color}]",
            classes="campaign-item-content",
        )


class HomeScreen(Screen):
    """
    The Hall of Chronicles - Home screen.

    Lists available campaigns and provides navigation to create new ones.
    """

    BINDINGS = [
        ("enter", "select_campaign", "Select"),
        ("n", "new_campaign", "New Tale"),
        ("d", "delete_campaign", "Delete"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the home screen layout."""
        with Container(id="home-container"):
            yield Static(SIMPLE_TITLE, id="title-art")
            yield Static(
                "Choose a tale to continue, or begin a new chronicle...",
                id="subtitle",
            )

            yield ListView(id="campaign-list")

            with Horizontal(id="action-buttons"):
                yield Button("📜 New Tale", id="btn-new", variant="primary", classes="action-button")
                yield Button("🔄 Refresh", id="btn-refresh", variant="default", classes="action-button")
                yield Button("⚙️ Settings", id="btn-settings", variant="default", classes="action-button")

    def on_mount(self) -> None:
        """Load campaigns when screen mounts."""
        self.load_campaigns()

    def load_campaigns(self) -> None:
        """Load and display available campaigns."""
        settings = get_settings()
        campaigns = []

        if settings.campaigns_path.exists():
            for campaign_dir in settings.campaigns_path.iterdir():
                if campaign_dir.is_dir():
                    campaign_file = campaign_dir / "campaign.json"
                    if campaign_file.exists():
                        try:
                            with open(campaign_file) as f:
                                data = json.load(f)
                                campaigns.append({
                                    "id": data.get("id", campaign_dir.name),
                                    "name": data.get("name", "Unknown"),
                                    "status": data.get("status", "unknown"),
                                    "turn": data.get("current_turn", 0),
                                    "sessions": data.get("total_sessions", 0),
                                    "setting": data.get("setting_summary", "")[:100],
                                })
                        except Exception:
                            pass

        # Update the list view
        list_view = self.query_one("#campaign-list", ListView)
        list_view.clear()

        if campaigns:
            for campaign in campaigns:
                list_view.append(CampaignListItem(campaign))
        else:
            list_view.append(
                ListItem(
                    Static(
                        "[italic]No chronicles found...\n\n"
                        "Press [bold]n[/bold] or click 'New Tale' to begin your first story.[/italic]",
                        id="no-campaigns",
                    )
                )
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-new":
            self.action_new_campaign()
        elif event.button.id == "btn-refresh":
            self.action_refresh()
        elif event.button.id == "btn-settings":
            self.notify("Settings not yet implemented", severity="information")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle campaign selection."""
        if isinstance(event.item, CampaignListItem):
            campaign_id = event.item.campaign_data.get("id")
            if campaign_id:
                self.app.load_campaign(campaign_id)

    def action_new_campaign(self) -> None:
        """Start the campaign creation wizard."""
        self.app.push_screen("scriptorium")

    def action_refresh(self) -> None:
        """Refresh the campaign list."""
        self.load_campaigns()
        self.notify("Chronicle list refreshed", severity="information")

    def action_select_campaign(self) -> None:
        """Select the highlighted campaign."""
        list_view = self.query_one("#campaign-list", ListView)
        if list_view.highlighted_child and isinstance(list_view.highlighted_child, CampaignListItem):
            campaign_id = list_view.highlighted_child.campaign_data.get("id")
            if campaign_id:
                self.app.load_campaign(campaign_id)

    def action_delete_campaign(self) -> None:
        """Delete the selected campaign (with confirmation)."""
        self.notify("Delete not yet implemented - use CLI for now", severity="warning")
