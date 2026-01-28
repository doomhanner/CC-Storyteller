"""
Entity Bible - The core data management system for campaign entities.

The Bible tracks all consequential entities in the story and their relationships.
It provides efficient access to entities, relationship queries, and state management.
"""

import json
from pathlib import Path
from typing import TypeVar

from storyteller.models.entities import (
    Character,
    Entity,
    EntityType,
    Faction,
    Item,
    Location,
    Lore,
)
from storyteller.models.relationships import Relationship, RelationshipType

E = TypeVar("E", bound=Entity)


class EntityBible:
    """
    The Entity Bible - manages all entities and relationships for a campaign.

    Provides:
    - CRUD operations for entities
    - Relationship management with bidirectional queries
    - Turn-indexed state tracking
    - Persistence to JSON files
    """

    def __init__(self, campaign_id: str, base_path: Path):
        self.campaign_id = campaign_id
        self.base_path = base_path / campaign_id / "bible"
        self.base_path.mkdir(parents=True, exist_ok=True)

        # In-memory storage
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}

        # Indexes for fast lookup
        self._by_type: dict[EntityType, set[str]] = {t: set() for t in EntityType}
        self._by_name: dict[str, set[str]] = {}  # name -> entity IDs
        self._relationships_by_source: dict[str, set[str]] = {}
        self._relationships_by_target: dict[str, set[str]] = {}

    # ==================== Entity CRUD ====================

    def add_entity(self, entity: Entity) -> Entity:
        """Add an entity to the bible."""
        self._entities[entity.id] = entity
        self._by_type[entity.type].add(entity.id)

        # Index by name (lowercased for case-insensitive lookup)
        name_key = entity.name.lower()
        if name_key not in self._by_name:
            self._by_name[name_key] = set()
        self._by_name[name_key].add(entity.id)

        # Index aliases too
        for alias in entity.aliases:
            alias_key = alias.lower()
            if alias_key not in self._by_name:
                self._by_name[alias_key] = set()
            self._by_name[alias_key].add(entity.id)

        return entity

    def get_entity(self, entity_id: str) -> Entity | None:
        """Get an entity by ID."""
        return self._entities.get(entity_id)

    def get_entity_typed(self, entity_id: str, entity_type: type[E]) -> E | None:
        """Get an entity by ID with type checking."""
        entity = self._entities.get(entity_id)
        if entity and isinstance(entity, entity_type):
            return entity
        return None

    def update_entity(self, entity: Entity, turn: int | None = None) -> Entity:
        """Update an entity in the bible."""
        if turn is not None:
            entity.update_turn(turn)
        self._entities[entity.id] = entity
        return entity

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity and all its relationships."""
        entity = self._entities.get(entity_id)
        if not entity:
            return False

        # Remove from indexes
        self._by_type[entity.type].discard(entity_id)

        name_key = entity.name.lower()
        if name_key in self._by_name:
            self._by_name[name_key].discard(entity_id)

        for alias in entity.aliases:
            alias_key = alias.lower()
            if alias_key in self._by_name:
                self._by_name[alias_key].discard(entity_id)

        # Remove related relationships
        for rel_id in list(self._relationships_by_source.get(entity_id, set())):
            self.remove_relationship(rel_id)
        for rel_id in list(self._relationships_by_target.get(entity_id, set())):
            self.remove_relationship(rel_id)

        del self._entities[entity_id]
        return True

    # ==================== Entity Queries ====================

    def find_by_name(self, name: str) -> list[Entity]:
        """Find entities by name or alias (case-insensitive)."""
        name_key = name.lower()
        entity_ids = self._by_name.get(name_key, set())
        return [self._entities[eid] for eid in entity_ids if eid in self._entities]

    def find_by_type(self, entity_type: EntityType) -> list[Entity]:
        """Get all entities of a given type."""
        return [
            self._entities[eid]
            for eid in self._by_type[entity_type]
            if eid in self._entities
        ]

    def get_characters(self) -> list[Character]:
        """Get all character entities."""
        return [
            e for e in self.find_by_type(EntityType.CHARACTER) if isinstance(e, Character)
        ]

    def get_locations(self) -> list[Location]:
        """Get all location entities."""
        return [
            e for e in self.find_by_type(EntityType.LOCATION) if isinstance(e, Location)
        ]

    def get_items(self) -> list[Item]:
        """Get all item entities."""
        return [e for e in self.find_by_type(EntityType.ITEM) if isinstance(e, Item)]

    def get_factions(self) -> list[Faction]:
        """Get all faction entities."""
        return [
            e for e in self.find_by_type(EntityType.FACTION) if isinstance(e, Faction)
        ]

    def get_lore(self) -> list[Lore]:
        """Get all lore entries."""
        return [e for e in self.find_by_type(EntityType.LORE) if isinstance(e, Lore)]

    def get_pc(self) -> Character | None:
        """Get the player character."""
        for char in self.get_characters():
            if char.is_pc:
                return char
        return None

    def search(self, query: str, entity_types: list[EntityType] | None = None) -> list[Entity]:
        """
        Search entities by name, aliases, description, or tags.
        Optionally filter by entity types.
        """
        query_lower = query.lower()
        results = []

        for entity in self._entities.values():
            if entity_types and entity.type not in entity_types:
                continue

            # Check name and aliases
            if query_lower in entity.name.lower():
                results.append(entity)
                continue

            if any(query_lower in alias.lower() for alias in entity.aliases):
                results.append(entity)
                continue

            # Check description
            if query_lower in entity.description.lower():
                results.append(entity)
                continue

            # Check tags
            if any(query_lower in tag.lower() for tag in entity.tags):
                results.append(entity)

        return results

    # ==================== Relationship Management ====================

    def add_relationship(self, relationship: Relationship) -> Relationship:
        """Add a relationship to the bible."""
        self._relationships[relationship.id] = relationship

        # Index by source
        if relationship.source_id not in self._relationships_by_source:
            self._relationships_by_source[relationship.source_id] = set()
        self._relationships_by_source[relationship.source_id].add(relationship.id)

        # Index by target
        if relationship.target_id not in self._relationships_by_target:
            self._relationships_by_target[relationship.target_id] = set()
        self._relationships_by_target[relationship.target_id].add(relationship.id)

        return relationship

    def get_relationship(self, rel_id: str) -> Relationship | None:
        """Get a relationship by ID."""
        return self._relationships.get(rel_id)

    def remove_relationship(self, rel_id: str) -> bool:
        """Remove a relationship."""
        rel = self._relationships.get(rel_id)
        if not rel:
            return False

        # Remove from indexes
        if rel.source_id in self._relationships_by_source:
            self._relationships_by_source[rel.source_id].discard(rel_id)
        if rel.target_id in self._relationships_by_target:
            self._relationships_by_target[rel.target_id].discard(rel_id)

        del self._relationships[rel_id]
        return True

    def get_relationships_from(
        self, source_id: str, rel_type: RelationshipType | None = None
    ) -> list[Relationship]:
        """Get all relationships where the entity is the source."""
        rel_ids = self._relationships_by_source.get(source_id, set())
        rels = [self._relationships[rid] for rid in rel_ids if rid in self._relationships]

        if rel_type:
            rels = [r for r in rels if r.relationship_type == rel_type]

        return rels

    def get_relationships_to(
        self, target_id: str, rel_type: RelationshipType | None = None
    ) -> list[Relationship]:
        """Get all relationships where the entity is the target."""
        rel_ids = self._relationships_by_target.get(target_id, set())
        rels = [self._relationships[rid] for rid in rel_ids if rid in self._relationships]

        if rel_type:
            rels = [r for r in rels if r.relationship_type == rel_type]

        return rels

    def get_all_relationships(self, entity_id: str) -> list[Relationship]:
        """Get all relationships involving an entity (as source or target)."""
        from_rels = self.get_relationships_from(entity_id)
        to_rels = self.get_relationships_to(entity_id)
        return from_rels + to_rels

    def find_relationship(
        self, source_id: str, target_id: str, rel_type: RelationshipType | None = None
    ) -> Relationship | None:
        """Find a specific relationship between two entities."""
        rels = self.get_relationships_from(source_id, rel_type)
        for rel in rels:
            if rel.target_id == target_id:
                return rel
        return None

    def get_related_entities(
        self, entity_id: str, rel_type: RelationshipType | None = None
    ) -> list[Entity]:
        """Get all entities related to the given entity."""
        related_ids = set()

        for rel in self.get_relationships_from(entity_id, rel_type):
            related_ids.add(rel.target_id)

        for rel in self.get_relationships_to(entity_id, rel_type):
            related_ids.add(rel.source_id)

        return [self._entities[eid] for eid in related_ids if eid in self._entities]

    # ==================== Convenience Methods ====================

    def get_character_inventory(self, character_id: str) -> list[Item]:
        """Get all items owned by a character."""
        rels = self.get_relationships_from(character_id, RelationshipType.OWNS)
        items = []
        for rel in rels:
            item = self.get_entity_typed(rel.target_id, Item)
            if item:
                items.append(item)
        return items

    def get_location_occupants(self, location_id: str) -> list[Character]:
        """Get all characters at a location."""
        rels = self.get_relationships_to(location_id, RelationshipType.LOCATED_AT)
        characters = []
        for rel in rels:
            char = self.get_entity_typed(rel.source_id, Character)
            if char:
                characters.append(char)
        return characters

    def get_faction_members(self, faction_id: str) -> list[Character]:
        """Get all members of a faction."""
        rels = self.get_relationships_to(faction_id, RelationshipType.MEMBER_OF)
        members = []
        for rel in rels:
            char = self.get_entity_typed(rel.source_id, Character)
            if char:
                members.append(char)
        return members

    def get_character_knowledge(self, character_id: str) -> list[Entity]:
        """Get all entities a character knows about."""
        return self.get_related_entities(character_id, RelationshipType.KNOWS_ABOUT)

    # ==================== Persistence ====================

    def save(self) -> None:
        """Save the bible to disk."""
        # Save entities by type
        entity_files = {
            EntityType.CHARACTER: "characters.json",
            EntityType.LOCATION: "locations.json",
            EntityType.ITEM: "items.json",
            EntityType.FACTION: "factions.json",
            EntityType.LORE: "lore.json",
        }

        for entity_type, filename in entity_files.items():
            entities = self.find_by_type(entity_type)
            data = [e.model_dump(mode="json") for e in entities]
            filepath = self.base_path / filename
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

        # Save relationships
        rel_data = [r.model_dump(mode="json") for r in self._relationships.values()]
        with open(self.base_path / "relationships.json", "w") as f:
            json.dump(rel_data, f, indent=2, default=str)

    def load(self) -> None:
        """Load the bible from disk."""
        # Entity type to class mapping
        type_classes = {
            EntityType.CHARACTER: Character,
            EntityType.LOCATION: Location,
            EntityType.ITEM: Item,
            EntityType.FACTION: Faction,
            EntityType.LORE: Lore,
        }

        entity_files = {
            EntityType.CHARACTER: "characters.json",
            EntityType.LOCATION: "locations.json",
            EntityType.ITEM: "items.json",
            EntityType.FACTION: "factions.json",
            EntityType.LORE: "lore.json",
        }

        # Clear existing data
        self._entities.clear()
        self._relationships.clear()
        self._by_type = {t: set() for t in EntityType}
        self._by_name.clear()
        self._relationships_by_source.clear()
        self._relationships_by_target.clear()

        # Load entities
        for entity_type, filename in entity_files.items():
            filepath = self.base_path / filename
            if filepath.exists():
                with open(filepath) as f:
                    data = json.load(f)
                    entity_class = type_classes[entity_type]
                    for item in data:
                        entity = entity_class.model_validate(item)
                        self.add_entity(entity)

        # Load relationships
        rel_path = self.base_path / "relationships.json"
        if rel_path.exists():
            with open(rel_path) as f:
                data = json.load(f)
                for item in data:
                    rel = Relationship.model_validate(item)
                    self.add_relationship(rel)

    # ==================== Statistics ====================

    def stats(self) -> dict[str, int]:
        """Get statistics about the bible."""
        return {
            "total_entities": len(self._entities),
            "characters": len(self._by_type[EntityType.CHARACTER]),
            "locations": len(self._by_type[EntityType.LOCATION]),
            "items": len(self._by_type[EntityType.ITEM]),
            "factions": len(self._by_type[EntityType.FACTION]),
            "lore": len(self._by_type[EntityType.LORE]),
            "relationships": len(self._relationships),
        }
