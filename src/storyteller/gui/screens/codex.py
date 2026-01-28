"""
Codex Screen - The Entity Bible Browser.

Browse and view all entities and relationships in the campaign.
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Label,
    ListItem,
    ListView,
    Markdown,
    Static,
    TabbedContent,
    TabPane,
)

from storyteller.bible.entity_bible import EntityBible
from storyteller.config import get_settings
from storyteller.models.entities import (
    Character,
    Entity,
    EntityType,
    Faction,
    Item,
    Location,
    Lore,
)
from storyteller.models.relationships import Relationship


class EntityListItem(ListItem):
    """An entity item in the sidebar list."""

    def __init__(self, entity: Entity) -> None:
        super().__init__()
        self.entity = entity

    def compose(self) -> ComposeResult:
        """Compose the entity item."""
        icon = {
            EntityType.CHARACTER: "👤",
            EntityType.LOCATION: "📍",
            EntityType.ITEM: "🗡️",
            EntityType.FACTION: "⚔️",
            EntityType.LORE: "📜",
        }.get(self.entity.type, "•")

        pc_badge = " [cyan]★[/cyan]" if isinstance(self.entity, Character) and self.entity.is_pc else ""

        yield Static(f"{icon} {self.entity.name}{pc_badge}")


class EntityDetailView(Static):
    """Detailed view of a selected entity."""

    def __init__(self, entity: Entity | None, bible: EntityBible) -> None:
        super().__init__()
        self.entity = entity
        self.bible = bible

    def compose(self) -> ComposeResult:
        """Compose the entity detail view."""
        if not self.entity:
            yield Static(
                "[italic]Select an entity from the list to view details.[/italic]",
                classes="loading",
            )
            return

        # Header
        yield Static(self.entity.name, id="entity-name")
        yield Static(
            f"{self.entity.type.value.title()} • {self.entity.turn_ref.to_tag()}",
            id="entity-type",
        )

        # Description
        if self.entity.description:
            yield Static("Description", classes="detail-header")
            yield Static(self.entity.description, classes="detail-content")

        # Type-specific details
        if isinstance(self.entity, Character):
            yield from self._compose_character_details(self.entity)
        elif isinstance(self.entity, Location):
            yield from self._compose_location_details(self.entity)
        elif isinstance(self.entity, Item):
            yield from self._compose_item_details(self.entity)
        elif isinstance(self.entity, Faction):
            yield from self._compose_faction_details(self.entity)
        elif isinstance(self.entity, Lore):
            yield from self._compose_lore_details(self.entity)

        # Relationships
        relationships = self.bible.get_all_relationships(self.entity.id)
        if relationships:
            yield Static("Relationships", classes="detail-header")
            yield from self._compose_relationships(relationships)

        # Tags
        if self.entity.tags:
            yield Static("Tags", classes="detail-header")
            yield Static(", ".join(self.entity.tags), classes="detail-content")

    def _compose_character_details(self, char: Character) -> ComposeResult:
        """Compose character-specific details."""
        # Physical
        if char.physical.appearance or char.physical.build:
            yield Static("Physical", classes="detail-header")
            content = []
            if char.physical.appearance:
                content.append(f"**Appearance:** {char.physical.appearance}")
            if char.physical.build:
                content.append(f"**Build:** {char.physical.build}")
            if char.physical.limitations:
                content.append(f"**Limitations:** {', '.join(char.physical.limitations)}")
            yield Markdown("\n\n".join(content), classes="detail-content")

        # Psychology
        psych = char.psychology
        if psych.wants_immediate or psych.wants_long_term or psych.fears:
            yield Static("Psychology", classes="detail-header")
            content = []
            if psych.wants_immediate:
                content.append(f"**Wants (now):** {psych.wants_immediate}")
            if psych.wants_long_term:
                content.append(f"**Wants (long-term):** {psych.wants_long_term}")
            if psych.fears:
                content.append(f"**Fears:** {', '.join(psych.fears)}")
            if psych.wounds:
                content.append(f"**Wounds:** {', '.join(psych.wounds)}")
            if psych.blindspots:
                content.append(f"**Blindspots:** {', '.join(psych.blindspots)}")
            yield Markdown("\n\n".join(content), classes="detail-content")

        # Voice
        voice = psych.voice
        if voice.patterns or voice.expressions:
            yield Static("Voice", classes="detail-header")
            content = []
            if voice.patterns:
                content.append(f"**Patterns:** {', '.join(voice.patterns)}")
            if voice.habits:
                content.append(f"**Habits:** {', '.join(voice.habits)}")
            if voice.expressions:
                content.append(f"**Expressions:** {', '.join(voice.expressions)}")
            yield Markdown("\n\n".join(content), classes="detail-content")

        # Information state
        info = char.information_state
        if info.knows or info.believes or info.suspects:
            yield Static("Information State", classes="detail-header")
            content = []
            if info.knows:
                content.append(f"**Knows:** {'; '.join(info.knows)}")
            if info.believes:
                content.append(f"**Believes:** {'; '.join(info.believes)}")
            if info.suspects:
                content.append(f"**Suspects:** {'; '.join(info.suspects)}")
            yield Markdown("\n\n".join(content), classes="detail-content")

    def _compose_location_details(self, loc: Location) -> ComposeResult:
        """Compose location-specific details."""
        if loc.atmosphere:
            yield Static("Atmosphere", classes="detail-header")
            yield Static(loc.atmosphere, classes="detail-content")

        if loc.notable_features:
            yield Static("Notable Features", classes="detail-header")
            yield Static("• " + "\n• ".join(loc.notable_features), classes="detail-content")

    def _compose_item_details(self, item: Item) -> ComposeResult:
        """Compose item-specific details."""
        if item.properties:
            yield Static("Properties", classes="detail-header")
            props = [f"**{k}:** {v}" for k, v in item.properties.items()]
            yield Markdown("\n\n".join(props), classes="detail-content")

        if item.history:
            yield Static("History", classes="detail-header")
            yield Static("• " + "\n• ".join(item.history), classes="detail-content")

    def _compose_faction_details(self, faction: Faction) -> ComposeResult:
        """Compose faction-specific details."""
        if faction.goals:
            yield Static("Goals", classes="detail-header")
            yield Static("• " + "\n• ".join(faction.goals), classes="detail-content")

        if faction.public_reputation:
            yield Static("Public Reputation", classes="detail-header")
            yield Static(faction.public_reputation, classes="detail-content")

        if faction.secret_nature:
            yield Static("Secret Nature", classes="detail-header")
            yield Static(f"[italic]{faction.secret_nature}[/italic]", classes="detail-content")

    def _compose_lore_details(self, lore: Lore) -> ComposeResult:
        """Compose lore-specific details."""
        yield Static(f"Category: {lore.category.value.title()}", classes="detail-content")

        if lore.content:
            yield Static("Content", classes="detail-header")
            yield Markdown(lore.content, classes="detail-content")

        visibility = "Common Knowledge" if lore.is_common_knowledge else "Secret/Restricted"
        yield Static(f"[italic]Visibility: {visibility}[/italic]", classes="detail-content")

    def _compose_relationships(self, relationships: list[Relationship]) -> ComposeResult:
        """Compose the relationships section."""
        for rel in relationships[:10]:  # Limit to 10
            # Get entity names
            source = self.bible.get_entity(rel.source_id)
            target = self.bible.get_entity(rel.target_id)

            source_name = source.name if source else rel.source_id
            target_name = target.name if target else rel.target_id

            # Determine direction indicator
            if rel.source_id == self.entity.id:
                direction = f"→ {target_name}"
            else:
                direction = f"← {source_name}"

            rel_desc = rel.describe()
            yield Static(
                f"  • {direction}: [cyan]{rel_desc}[/cyan]",
                classes="detail-content",
            )


class CodexScreen(Screen):
    """
    The Codex - Entity Bible Browser.

    Browse all entities (Characters, Locations, Items, Factions, Lore)
    and their relationships.
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("tab", "next_tab", "Next Tab"),
        ("shift+tab", "prev_tab", "Prev Tab"),
    ]

    def __init__(self, campaign_id: str) -> None:
        super().__init__()
        self.campaign_id = campaign_id
        self.bible: EntityBible | None = None
        self.selected_entity: Entity | None = None

    def compose(self) -> ComposeResult:
        """Compose the codex screen layout."""
        with Horizontal(id="codex-container"):
            with Vertical(id="codex-sidebar"):
                yield Static(
                    "╔═══════════════════╗\n"
                    "║     THE CODEX     ║\n"
                    "╚═══════════════════╝",
                    classes="panel-title",
                )
                with TabbedContent(id="entity-tabs"):
                    with TabPane("Characters", id="tab-characters"):
                        yield ListView(id="list-characters")
                    with TabPane("Locations", id="tab-locations"):
                        yield ListView(id="list-locations")
                    with TabPane("Items", id="tab-items"):
                        yield ListView(id="list-items")
                    with TabPane("Factions", id="tab-factions"):
                        yield ListView(id="list-factions")
                    with TabPane("Lore", id="tab-lore"):
                        yield ListView(id="list-lore")

            with ScrollableContainer(id="codex-detail"):
                yield EntityDetailView(None, None)

    def on_mount(self) -> None:
        """Load the bible when screen mounts."""
        self.load_bible()

    def load_bible(self) -> None:
        """Load the entity bible."""
        settings = get_settings()
        self.bible = EntityBible(self.campaign_id, settings.campaigns_path)
        self.bible.load()

        # Populate lists
        self._populate_list("list-characters", self.bible.get_characters())
        self._populate_list("list-locations", self.bible.get_locations())
        self._populate_list("list-items", self.bible.get_items())
        self._populate_list("list-factions", self.bible.get_factions())
        self._populate_list("list-lore", self.bible.get_lore())

    def _populate_list(self, list_id: str, entities: list[Entity]) -> None:
        """Populate a list with entities."""
        try:
            list_view = self.query_one(f"#{list_id}", ListView)
            list_view.clear()

            if entities:
                for entity in entities:
                    list_view.append(EntityListItem(entity))
            else:
                list_view.append(
                    ListItem(Static("[italic]No entries[/italic]"))
                )
        except Exception:
            pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle entity selection."""
        if isinstance(event.item, EntityListItem):
            self.selected_entity = event.item.entity
            self.update_detail_view()

    def update_detail_view(self) -> None:
        """Update the detail view with selected entity."""
        detail_container = self.query_one("#codex-detail", ScrollableContainer)
        detail_container.remove_children()
        detail_container.mount(EntityDetailView(self.selected_entity, self.bible))

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    def action_next_tab(self) -> None:
        """Switch to next tab."""
        tabs = self.query_one("#entity-tabs", TabbedContent)
        # TabbedContent doesn't have next_tab, so we handle manually
        self.notify("Use mouse to switch tabs", severity="information")

    def action_prev_tab(self) -> None:
        """Switch to previous tab."""
        self.notify("Use mouse to switch tabs", severity="information")
