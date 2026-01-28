"""
Scriptorium Screen - The Campaign Creation Wizard.

Create new campaigns with guided input and AI generation.
"""

import asyncio

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Input,
    Label,
    LoadingIndicator,
    Markdown,
    ProgressBar,
    Static,
    TextArea,
)
from textual.worker import Worker, WorkerState

from storyteller.config import get_settings
from storyteller.generation.campaign_generator import CampaignGenerator, GenerationInput
from storyteller.models.campaign import CampaignStatus
from storyteller.session.session_manager import SessionManager


class WizardStep(Static):
    """A step in the campaign creation wizard."""

    def __init__(
        self,
        step_number: int,
        title: str,
        description: str,
        input_widget: Input | TextArea,
    ) -> None:
        super().__init__(classes="wizard-step")
        self.step_number = step_number
        self.title = title
        self.description = description
        self.input_widget = input_widget

    def compose(self) -> ComposeResult:
        """Compose the wizard step."""
        yield Static(f"[bold]Step {self.step_number}: {self.title}[/bold]", classes="step-title")
        yield Static(f"[italic]{self.description}[/italic]", classes="step-description")
        yield self.input_widget


class CreativitySlider(Static):
    """A creativity level selector."""

    def __init__(self, initial_value: float = 0.5) -> None:
        super().__init__()
        self.value = initial_value

    def compose(self) -> ComposeResult:
        """Compose the creativity slider."""
        yield Static("[bold]Creativity Level[/bold]", classes="step-title")
        yield Static(
            "[italic]How much should the Archivist elaborate on your input?[/italic]",
            classes="step-description",
        )
        with Horizontal(classes="creativity-buttons"):
            yield Button("Low", id="creativity-low", variant="default")
            yield Button("Medium", id="creativity-medium", variant="primary")
            yield Button("High", id="creativity-high", variant="default")
        yield Static(
            id="creativity-description",
            classes="detail-content",
        )

    def on_mount(self) -> None:
        """Set initial state."""
        self._update_description()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle creativity button presses."""
        # Reset all buttons
        self.query_one("#creativity-low", Button).variant = "default"
        self.query_one("#creativity-medium", Button).variant = "default"
        self.query_one("#creativity-high", Button).variant = "default"

        # Set selected button
        if event.button.id == "creativity-low":
            self.value = 0.25
            event.button.variant = "primary"
        elif event.button.id == "creativity-medium":
            self.value = 0.5
            event.button.variant = "primary"
        elif event.button.id == "creativity-high":
            self.value = 0.85
            event.button.variant = "primary"

        self._update_description()

    def _update_description(self) -> None:
        """Update the description based on current value."""
        desc_widget = self.query_one("#creativity-description", Static)

        if self.value < 0.35:
            desc_widget.update(
                "[dim]Minimal elaboration. The Archivist will stay close to your "
                "exact input, adding only essential details needed for play.[/dim]"
            )
        elif self.value < 0.7:
            desc_widget.update(
                "[dim]Balanced elaboration. The Archivist will flesh out your ideas "
                "with reasonable additions while respecting your core vision.[/dim]"
            )
        else:
            desc_widget.update(
                "[dim]Rich elaboration. The Archivist will create deep characterization, "
                "hidden connections, and layered complexity from your seeds.[/dim]"
            )


class ScriptoriumScreen(Screen):
    """
    The Scriptorium - Campaign Creation Wizard.

    Guide the user through creating a new campaign with AI assistance.
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+enter", "generate", "Generate"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.generator: CampaignGenerator | None = None
        self._generating = False

    def compose(self) -> ComposeResult:
        """Compose the scriptorium screen layout."""
        with ScrollableContainer(id="scriptorium-container"):
            yield Static(
                "╔════════════════════════════════════════════╗\n"
                "║          T H E   S C R I P T O R I U M     ║\n"
                "║           Campaign Creation Wizard         ║\n"
                "╚════════════════════════════════════════════╝",
                id="scriptorium-title",
            )
            yield Static(
                "Inscribe the foundations of your tale...",
                id="scriptorium-subtitle",
            )

            # Campaign name
            with Container(classes="wizard-step"):
                yield Static("[bold]Campaign Name[/bold]", classes="step-title")
                yield Input(
                    placeholder="Enter a name for your chronicle...",
                    id="input-name",
                    classes="wizard-input",
                )

            # Setting description
            with Container(classes="wizard-step"):
                yield Static("[bold]Step 1: The Setting[/bold]", classes="step-title")
                yield Static(
                    "[italic]Describe your world—its genre, tone, rules, and atmosphere.[/italic]",
                    classes="step-description",
                )
                yield TextArea(
                    id="input-setting",
                    classes="wizard-textarea",
                )

            # Player character
            with Container(classes="wizard-step"):
                yield Static("[bold]Step 2: The Protagonist[/bold]", classes="step-title")
                yield Static(
                    "[italic]Who is your character? Their appearance, abilities, personality, goals.[/italic]",
                    classes="step-description",
                )
                yield TextArea(
                    id="input-pc",
                    classes="wizard-textarea",
                )

            # Starting situation
            with Container(classes="wizard-step"):
                yield Static("[bold]Step 3: The Beginning[/bold]", classes="step-title")
                yield Static(
                    "[italic]Where does your story begin? What situation does the protagonist find themselves in?[/italic]",
                    classes="step-description",
                )
                yield TextArea(
                    id="input-start",
                    classes="wizard-textarea",
                )

            # Additional notes
            with Container(classes="wizard-step"):
                yield Static("[bold]Step 4: Additional Notes (Optional)[/bold]", classes="step-title")
                yield Static(
                    "[italic]Any other details—NPCs, factions, plot hooks, world lore, or extensive notes to import.[/italic]",
                    classes="step-description",
                )
                yield TextArea(
                    id="input-notes",
                    classes="wizard-textarea",
                )

            # Creativity slider
            yield CreativitySlider()

            # Action buttons
            with Horizontal(id="wizard-buttons"):
                yield Button("Cancel", id="btn-cancel", variant="error", classes="wizard-button")
                yield Button(
                    "📜 Inscribe Chronicle",
                    id="btn-generate",
                    variant="success",
                    classes="wizard-button",
                )

            # Generation progress (hidden initially)
            with Container(id="generation-progress"):
                yield Static("", id="generation-status")
                yield LoadingIndicator(id="generation-spinner")

    def on_mount(self) -> None:
        """Initialize the screen."""
        # Hide generation progress initially
        self.query_one("#generation-progress", Container).display = False
        self.query_one("#generation-spinner", LoadingIndicator).display = False

        # Check for API key
        settings = get_settings()
        if not settings.anthropic_api_key:
            self.notify(
                "ANTHROPIC_API_KEY not set. Please configure it before generating.",
                severity="warning",
                timeout=5,
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-generate":
            self.action_generate()

    def action_cancel(self) -> None:
        """Cancel and go back."""
        self.app.pop_screen()

    def action_generate(self) -> None:
        """Generate the campaign."""
        if self._generating:
            return

        # Gather input
        name = self.query_one("#input-name", Input).value.strip()
        setting = self.query_one("#input-setting", TextArea).text.strip()
        pc = self.query_one("#input-pc", TextArea).text.strip()
        start = self.query_one("#input-start", TextArea).text.strip()
        notes = self.query_one("#input-notes", TextArea).text.strip()
        creativity = self.query_one(CreativitySlider).value

        # Validate
        if not setting and not pc and not start:
            self.notify(
                "Please provide at least some description of your setting, character, or starting situation.",
                severity="warning",
            )
            return

        # Show progress
        self._generating = True
        self.query_one("#wizard-buttons", Horizontal).display = False
        progress = self.query_one("#generation-progress", Container)
        progress.display = True

        status = self.query_one("#generation-status", Static)
        status.update("[bold]The Archivist is inscribing your chronicle...[/bold]")

        spinner = self.query_one("#generation-spinner", LoadingIndicator)
        spinner.display = True

        # Run generation
        input_data = GenerationInput(
            campaign_name=name or "Untitled Chronicle",
            setting_description=setting,
            pc_description=pc,
            starting_situation=start,
            additional_notes=notes,
            creativity=creativity,
        )

        self.run_worker(self._generate_campaign(input_data), exclusive=True)

    async def _generate_campaign(self, input_data: GenerationInput) -> None:
        """Generate the campaign asynchronously."""
        try:
            generator = CampaignGenerator()
            result = await generator.generate_campaign(input_data)

            # Update status
            status = self.query_one("#generation-status", Static)
            status.update("[bold green]Chronicle inscribed successfully![/bold green]")

            # Hide spinner
            self.query_one("#generation-spinner", LoadingIndicator).display = False

            # Show summary
            await asyncio.sleep(0.5)

            # Save the campaign
            result.campaign.status = CampaignStatus.READY
            manager = SessionManager(result.campaign, result.bible, result.world_state)
            manager.save()

            # Show success notification
            self.notify(
                f"Created '{result.campaign.name}' with "
                f"{result.bible.stats()['total_entities']} entities",
                severity="information",
                timeout=3,
            )

            # Brief pause then load the campaign
            await asyncio.sleep(1)
            self.app.current_campaign_id = result.campaign.id
            self.app.pop_screen()
            self.app.push_screen("chronicle")
            self.app.load_campaign(result.campaign.id)

        except Exception as e:
            self.notify(f"Generation failed: {e}", severity="error")
            self._generating = False
            self.query_one("#wizard-buttons", Horizontal).display = True
            self.query_one("#generation-progress", Container).display = False

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        if event.state == WorkerState.ERROR:
            self.notify("Campaign generation failed", severity="error")
            self._generating = False
            self.query_one("#wizard-buttons", Horizontal).display = True
            self.query_one("#generation-progress", Container).display = False
