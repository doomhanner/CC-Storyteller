"""Campaigns API routes."""

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from storyteller.api.deps import AppSettings
from storyteller.api.schemas import (
    CampaignCreateRequest,
    CampaignCreateResponse,
    CampaignListResponse,
    CampaignSummary,
)
from storyteller.generation.campaign_generator import CampaignGenerator, GenerationInput
from storyteller.models.campaign import CampaignStatus

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _load_campaign_summary(campaign_dir: Path) -> CampaignSummary | None:
    """Load campaign summary from directory."""
    campaign_file = campaign_dir / "campaign.json"
    if not campaign_file.exists():
        return None

    try:
        with open(campaign_file) as f:
            data = json.load(f)
            return CampaignSummary(
                id=data.get("id", campaign_dir.name),
                name=data.get("name", "Unknown"),
                status=data.get("status", "unknown"),
                current_turn=data.get("current_turn", 0),
                total_sessions=data.get("total_sessions", 0),
                setting_summary=data.get("setting_summary", "")[:200],
                created_at=data.get("created_at"),
                updated_at=data.get("updated_at"),
            )
    except Exception:
        return None


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(settings: AppSettings) -> CampaignListResponse:
    """List all campaigns."""
    campaigns: list[CampaignSummary] = []

    campaigns_path = settings.campaigns_path
    if not campaigns_path.exists():
        return CampaignListResponse(campaigns=[], total=0)

    for campaign_dir in campaigns_path.iterdir():
        if campaign_dir.is_dir():
            summary = _load_campaign_summary(campaign_dir)
            if summary:
                campaigns.append(summary)

    # Sort by updated_at descending
    campaigns.sort(key=lambda c: c.updated_at or "", reverse=True)

    return CampaignListResponse(campaigns=campaigns, total=len(campaigns))


@router.get("/{campaign_id}", response_model=CampaignSummary)
async def get_campaign(campaign_id: str, settings: AppSettings) -> CampaignSummary:
    """Get campaign details."""
    campaign_dir = settings.campaigns_path / campaign_id
    if not campaign_dir.exists():
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found")

    summary = _load_campaign_summary(campaign_dir)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found")

    return summary


@router.post("", response_model=CampaignCreateResponse)
async def create_campaign(
    request: CampaignCreateRequest,
    settings: AppSettings,
) -> CampaignCreateResponse:
    """Create a new campaign."""
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=400,
            detail="Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env file.",
        )

    generator = CampaignGenerator()
    input_data = GenerationInput(
        campaign_name=request.name,
        setting_description=request.setting_description,
        pc_description=request.pc_description,
        starting_situation=request.starting_situation,
        additional_notes=request.additional_notes,
        creativity=request.creativity,
    )

    result = await generator.generate_campaign(input_data)

    # Save the campaign
    from storyteller.session.session_manager import SessionManager

    result.campaign.status = CampaignStatus.READY
    manager = SessionManager(result.campaign, result.bible, result.world_state)
    manager.save()

    # Get bible stats
    stats = result.bible.stats()

    campaign_summary = CampaignSummary(
        id=result.campaign.id,
        name=result.campaign.name,
        status=result.campaign.status.value,
        current_turn=result.campaign.current_turn,
        total_sessions=result.campaign.total_sessions,
        setting_summary=result.campaign.setting_summary[:200] if result.campaign.setting_summary else "",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )

    return CampaignCreateResponse(
        campaign=campaign_summary,
        expansion_summary=result.expansion_summary,
        bible_stats=stats,
        tokens_used=result.tokens_used,
        warnings=result.warnings,
    )


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str, settings: AppSettings) -> dict:
    """Delete a campaign."""
    import shutil

    campaign_dir = settings.campaigns_path / campaign_id
    if not campaign_dir.exists():
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found")

    try:
        shutil.rmtree(campaign_dir)
        return {"message": f"Campaign '{campaign_id}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete campaign: {str(e)}")
