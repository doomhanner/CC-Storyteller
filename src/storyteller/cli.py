"""
Command-line interface for CC-Storyteller.

Provides commands for:
- Creating new campaigns
- Loading and playing existing campaigns
- Managing the Entity Bible
- Configuration
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, Prompt
from rich.table import Table
from rich.theme import Theme

from storyteller.config import get_settings
from storyteller.generation.campaign_generator import CampaignGenerator, GenerationInput
from storyteller.models.campaign import CampaignStatus
from storyteller.session.session_manager import SessionManager

# Custom theme for the app
custom_theme = Theme(
    {
        "narrative": "italic",
        "ooc": "dim cyan",
        "npc": "bold yellow",
        "location": "bold green",
        "time": "dim",
        "command": "bold magenta",
    }
)

console = Console(theme=custom_theme)
app = typer.Typer(
    name="storyteller",
    help="CC-Storyteller: LLM-powered narrative simulation engine",
    no_args_is_help=True,
)


def print_narrative(text: str) -> None:
    """Print narrative text with formatting."""
    # Check for turn tag
    if "{T:" in text:
        parts = text.rsplit("{T:", 1)
        narrative = parts[0].strip()
        turn_tag = "{T:" + parts[1] if len(parts) > 1 else ""
        console.print(Panel(Markdown(narrative), border_style="blue"))
        if turn_tag:
            console.print(f"[time]{turn_tag}[/time]")
    elif text.startswith("[OOC]"):
        console.print(Panel(text, border_style="cyan", title="OOC"))
    else:
        console.print(Panel(Markdown(text), border_style="blue"))


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]Success:[/bold green] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[dim]{message}[/dim]")


# ==================== Commands ====================


@app.command()
def new(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Campaign name"),
    creativity: float = typer.Option(
        0.5, "--creativity", "-c", help="Creativity level (0.0-1.0)"
    ),
    interactive: bool = typer.Option(
        True, "--interactive/--no-interactive", "-i/-I", help="Interactive mode"
    ),
) -> None:
    """Create a new campaign."""
    settings = get_settings()

    if not settings.anthropic_api_key:
        print_error("ANTHROPIC_API_KEY not set. Please set it in .env or environment.")
        raise typer.Exit(1)

    console.print(
        Panel(
            "[bold]CC-Storyteller[/bold]\n[dim]Campaign Creation Wizard[/dim]",
            border_style="green",
        )
    )

    # Gather input
    if interactive:
        console.print("\n[bold]Let's create your campaign![/bold]\n")

        campaign_name = name or Prompt.ask("Campaign name", default="New Campaign")

        console.print("\n[dim]Describe your setting (world, genre, tone):[/dim]")
        setting = Prompt.ask("Setting")

        console.print("\n[dim]Describe your player character:[/dim]")
        pc = Prompt.ask("PC")

        console.print("\n[dim]Describe the starting situation:[/dim]")
        start = Prompt.ask("Start")

        console.print("\n[dim]Any additional notes? (press Enter to skip):[/dim]")
        notes = Prompt.ask("Notes", default="")

        creativity = FloatPrompt.ask(
            "Creativity level (0.0=minimal, 1.0=expansive)",
            default=creativity,
        )
    else:
        campaign_name = name or "New Campaign"
        setting = ""
        pc = ""
        start = ""
        notes = ""

    # Generate the campaign
    console.print("\n[bold]Generating campaign...[/bold]")

    with console.status("[bold green]Creating your world..."):
        generator = CampaignGenerator()
        input_data = GenerationInput(
            campaign_name=campaign_name,
            setting_description=setting,
            pc_description=pc,
            starting_situation=start,
            additional_notes=notes,
            creativity=creativity,
        )

        result = asyncio.run(generator.generate_campaign(input_data))

    # Show results
    console.print("\n")
    console.print(Panel(Markdown(result.expansion_summary), title="Campaign Created"))

    if result.warnings:
        for warning in result.warnings:
            console.print(f"[yellow]Warning:[/yellow] {warning}")

    # Show bible stats
    stats = result.bible.stats()
    table = Table(title="Entity Bible")
    table.add_column("Type", style="cyan")
    table.add_column("Count", style="green")

    table.add_row("Characters", str(stats["characters"]))
    table.add_row("Locations", str(stats["locations"]))
    table.add_row("Items", str(stats["items"]))
    table.add_row("Factions", str(stats["factions"]))
    table.add_row("Lore", str(stats["lore"]))
    table.add_row("Relationships", str(stats["relationships"]))

    console.print(table)

    console.print(f"\n[dim]Tokens used: {result.tokens_used}[/dim]")

    # Confirm or edit
    if interactive:
        if Confirm.ask("\nReady to begin?"):
            result.campaign.status = CampaignStatus.READY
            # Save and start playing
            manager = SessionManager(result.campaign, result.bible, result.world_state)
            manager.save()
            print_success(f"Campaign '{result.campaign.name}' created!")
            console.print(f"\n[dim]Campaign ID: {result.campaign.id}[/dim]")
            console.print("\n[bold]Starting game...[/bold]\n")
            _play_loop(manager)
        else:
            console.print("[dim]Campaign saved as draft. Use 'storyteller play' to continue.[/dim]")
            manager = SessionManager(result.campaign, result.bible, result.world_state)
            manager.save()
    else:
        result.campaign.status = CampaignStatus.READY
        manager = SessionManager(result.campaign, result.bible, result.world_state)
        manager.save()
        print_success(f"Campaign '{result.campaign.name}' created!")
        console.print(f"Campaign ID: {result.campaign.id}")


@app.command()
def play(
    campaign_id: Optional[str] = typer.Argument(None, help="Campaign ID to play"),
) -> None:
    """Play an existing campaign."""
    settings = get_settings()

    if not settings.anthropic_api_key:
        print_error("ANTHROPIC_API_KEY not set. Please set it in .env or environment.")
        raise typer.Exit(1)

    # List campaigns if no ID provided
    if not campaign_id:
        campaigns = list_campaigns_internal()
        if not campaigns:
            print_info("No campaigns found. Use 'storyteller new' to create one.")
            raise typer.Exit(0)

        console.print("\n[bold]Available Campaigns:[/bold]\n")
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Turn", style="dim")

        for c in campaigns:
            table.add_row(c["id"], c["name"], c["status"], str(c["turn"]))

        console.print(table)
        campaign_id = Prompt.ask("\nEnter campaign ID to play")

    # Load the campaign
    try:
        manager = SessionManager.load(campaign_id)
    except FileNotFoundError:
        print_error(f"Campaign '{campaign_id}' not found.")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold]{manager.campaign.name}[/bold]\n[dim]{manager.campaign.setting_summary[:100]}...[/dim]",
            border_style="green",
        )
    )

    # Start playing
    _play_loop(manager)


@app.command("list")
def list_campaigns() -> None:
    """List all campaigns."""
    campaigns = list_campaigns_internal()

    if not campaigns:
        print_info("No campaigns found. Use 'storyteller new' to create one.")
        return

    table = Table(title="Campaigns")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Turn", style="dim")
    table.add_column("Sessions", style="dim")

    for c in campaigns:
        table.add_row(
            c["id"], c["name"], c["status"], str(c["turn"]), str(c["sessions"])
        )

    console.print(table)


@app.command()
def bible(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    entity_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by entity type"
    ),
) -> None:
    """View the Entity Bible for a campaign."""
    settings = get_settings()
    campaign_path = settings.campaigns_path / campaign_id

    if not campaign_path.exists():
        print_error(f"Campaign '{campaign_id}' not found.")
        raise typer.Exit(1)

    from storyteller.bible.entity_bible import EntityBible

    bible = EntityBible(campaign_id, settings.campaigns_path)
    bible.load()

    # Show stats
    stats = bible.stats()
    console.print(f"\n[bold]Entity Bible for {campaign_id}[/bold]\n")

    table = Table(title="Summary")
    table.add_column("Type", style="cyan")
    table.add_column("Count", style="green")

    table.add_row("Characters", str(stats["characters"]))
    table.add_row("Locations", str(stats["locations"]))
    table.add_row("Items", str(stats["items"]))
    table.add_row("Factions", str(stats["factions"]))
    table.add_row("Lore", str(stats["lore"]))
    table.add_row("Relationships", str(stats["relationships"]))

    console.print(table)

    # Show entities of requested type
    if entity_type:
        from storyteller.models.entities import EntityType

        try:
            etype = EntityType(entity_type.lower())
        except ValueError:
            print_error(f"Unknown entity type: {entity_type}")
            raise typer.Exit(1)

        entities = bible.find_by_type(etype)
        console.print(f"\n[bold]{entity_type.title()} Entities:[/bold]\n")

        for entity in entities:
            console.print(f"[cyan]{entity.id}[/cyan] - [green]{entity.name}[/green]")
            if entity.description:
                console.print(f"  [dim]{entity.description[:100]}...[/dim]")


@app.command()
def config() -> None:
    """Show current configuration."""
    settings = get_settings()

    console.print("\n[bold]Configuration[/bold]\n")

    table = Table()
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Data Directory", str(settings.data_dir))
    table.add_row("Campaigns Path", str(settings.campaigns_path))
    table.add_row(
        "API Key Set", "Yes" if settings.anthropic_api_key else "[red]No[/red]"
    )
    table.add_row("Storyteller Model", settings.models.storyteller_model)
    table.add_row("Archivist Model", settings.models.archivist_model)
    table.add_row("Debug Mode", "Yes" if settings.debug else "No")

    console.print(table)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
) -> None:
    """Start the web UI server."""
    import uvicorn

    console.print(
        Panel(
            "[bold]CC-Storyteller Web Server[/bold]\n"
            f"[dim]Starting at http://{host}:{port}[/dim]",
            border_style="green",
        )
    )

    console.print("\n[dim]Press Ctrl+C to stop the server[/dim]\n")

    uvicorn.run(
        "storyteller.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="debug" if debug else "info",
    )


# ==================== Internal Functions ====================


def list_campaigns_internal() -> list[dict]:
    """List all campaigns (internal)."""
    settings = get_settings()
    campaigns = []

    if not settings.campaigns_path.exists():
        return campaigns

    for campaign_dir in settings.campaigns_path.iterdir():
        if campaign_dir.is_dir():
            campaign_file = campaign_dir / "campaign.json"
            if campaign_file.exists():
                try:
                    with open(campaign_file) as f:
                        data = json.load(f)
                        campaigns.append(
                            {
                                "id": data.get("id", campaign_dir.name),
                                "name": data.get("name", "Unknown"),
                                "status": data.get("status", "unknown"),
                                "turn": data.get("current_turn", 0),
                                "sessions": data.get("total_sessions", 0),
                            }
                        )
                except Exception:
                    pass

    return campaigns


def _play_loop(manager: SessionManager) -> None:
    """Main gameplay loop."""
    # Start session
    opening = manager.start_session()
    print_narrative(opening)

    console.print(
        "\n[dim]Enter your actions, dialogue, or commands. Type ((help)) for help, ((quit)) to exit.[/dim]\n"
    )

    while True:
        try:
            # Get player input
            player_input = Prompt.ask("[bold cyan]>[/bold cyan]")

            if not player_input.strip():
                continue

            # Check for quit
            if player_input.strip().lower() in ["((quit))", "quit", "exit", "q"]:
                if Confirm.ask("Save and quit?"):
                    manager.save()
                    print_success("Game saved. Goodbye!")
                break

            # Process turn
            with console.status("[bold green]Processing..."):
                result = asyncio.run(manager.process_turn(player_input))

            # Display result
            print_narrative(result.narrative)

            if result.warnings:
                for warning in result.warnings:
                    console.print(f"[yellow]Warning:[/yellow] {warning}")

        except KeyboardInterrupt:
            console.print("\n")
            if Confirm.ask("Save and quit?"):
                manager.save()
                print_success("Game saved. Goodbye!")
            break
        except Exception as e:
            print_error(f"An error occurred: {e}")
            if Confirm.ask("Continue playing?"):
                continue
            else:
                manager.save()
                break


# ==================== Entry Point ====================


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
