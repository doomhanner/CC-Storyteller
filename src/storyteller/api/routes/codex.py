"""Codex (Entity Bible) API routes."""

from fastapi import APIRouter, HTTPException

from storyteller.api.deps import AppSettings
from storyteller.api.schemas import (
    CodexResponse,
    EntityDetail,
    EntitySummary,
    EntityType,
    RelationshipGraphResponse,
    RelationshipSummary,
)
from storyteller.bible.entity_bible import EntityBible
from storyteller.models.entities import EntityType as ModelEntityType

router = APIRouter(prefix="/codex", tags=["codex"])


def _get_bible(campaign_id: str, settings: AppSettings) -> EntityBible:
    """Get the entity bible for a campaign."""
    campaign_path = settings.campaigns_path / campaign_id
    if not campaign_path.exists():
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found")

    bible = EntityBible(campaign_id, settings.campaigns_path)
    bible.load()
    return bible


def _entity_to_summary(entity) -> EntitySummary:
    """Convert an entity to summary schema."""
    return EntitySummary(
        id=entity.id,
        name=entity.name,
        type=EntityType(entity.type.value),
        description=entity.description[:200] if entity.description else "",
        tags=entity.tags,
    )


def _relationship_to_summary(rel, bible: EntityBible) -> RelationshipSummary:
    """Convert a relationship to summary schema."""
    source = bible.get_entity(rel.source_id)
    target = bible.get_entity(rel.target_id)

    return RelationshipSummary(
        id=rel.id,
        source_id=rel.source_id,
        source_name=source.name if source else "Unknown",
        target_id=rel.target_id,
        target_name=target.name if target else "Unknown",
        relationship_type=rel.relationship_type.value,
        description=rel.description or "",
    )


@router.get("/{campaign_id}/entities", response_model=CodexResponse)
async def list_entities(
    campaign_id: str,
    settings: AppSettings,
    entity_type: EntityType | None = None,
) -> CodexResponse:
    """List all entities in a campaign's bible."""
    bible = _get_bible(campaign_id, settings)

    if entity_type:
        model_type = ModelEntityType(entity_type.value)
        entities = bible.find_by_type(model_type)
    else:
        entities = bible.get_all_entities()

    summaries = [_entity_to_summary(e) for e in entities]

    return CodexResponse(entities=summaries, total=len(summaries))


@router.get("/{campaign_id}/entities/{entity_id}", response_model=EntityDetail)
async def get_entity(
    campaign_id: str,
    entity_id: str,
    settings: AppSettings,
) -> EntityDetail:
    """Get detailed information about an entity."""
    bible = _get_bible(campaign_id, settings)

    entity = bible.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

    # Get relationships
    relationships = bible.get_entity_relationships(entity_id)
    rel_summaries = [_relationship_to_summary(r, bible) for r in relationships]

    return EntityDetail(
        id=entity.id,
        name=entity.name,
        type=EntityType(entity.type.value),
        description=entity.description or "",
        attributes=entity.attributes,
        tags=entity.tags,
        relationships=rel_summaries,
        turn_created=entity.turn_created,
        turn_modified=entity.turn_modified,
    )


@router.get("/{campaign_id}/relationships", response_model=RelationshipGraphResponse)
async def get_relationship_graph(
    campaign_id: str,
    settings: AppSettings,
) -> RelationshipGraphResponse:
    """Get the full relationship graph for visualization."""
    bible = _get_bible(campaign_id, settings)

    # Get all entities as nodes
    entities = bible.get_all_entities()
    nodes = [_entity_to_summary(e) for e in entities]

    # Get all relationships as edges
    edges = []
    seen_relationships = set()

    for entity in entities:
        relationships = bible.get_entity_relationships(entity.id)
        for rel in relationships:
            if rel.id not in seen_relationships:
                edges.append(_relationship_to_summary(rel, bible))
                seen_relationships.add(rel.id)

    return RelationshipGraphResponse(nodes=nodes, edges=edges)


@router.get("/{campaign_id}/stats")
async def get_bible_stats(campaign_id: str, settings: AppSettings) -> dict:
    """Get statistics about the entity bible."""
    bible = _get_bible(campaign_id, settings)
    return bible.stats()
