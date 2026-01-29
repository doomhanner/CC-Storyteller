"""Sessions API routes with WebSocket support."""

import asyncio
import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from storyteller.api.deps import AppSettings, get_app_settings
from storyteller.api.schemas import (
    SessionInfo,
    SessionStartRequest,
    SessionStartResponse,
    TurnRequest,
    TurnResponse,
    WSMessage,
    WSMessageType,
)
from storyteller.session.session_manager import SessionManager

router = APIRouter(prefix="/sessions", tags=["sessions"])

# Active sessions storage (in production, use Redis or similar)
_active_sessions: dict[str, SessionManager] = {}


def _get_session_manager(session_id: str) -> SessionManager:
    """Get an active session manager."""
    if session_id not in _active_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found or expired")
    return _active_sessions[session_id]


@router.post("", response_model=SessionStartResponse)
async def start_session(
    request: SessionStartRequest,
    settings: AppSettings,
) -> SessionStartResponse:
    """Start a new gameplay session."""
    try:
        manager = SessionManager.load(request.campaign_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Campaign '{request.campaign_id}' not found")

    # Generate session ID
    session_id = str(uuid4())[:8]

    # Start the session
    opening = manager.start_session()

    # Store the session
    _active_sessions[session_id] = manager

    session_info = SessionInfo(
        id=session_id,
        campaign_id=request.campaign_id,
        started_at=datetime.now().isoformat(),
        current_turn=manager.campaign.current_turn,
        is_active=True,
    )

    return SessionStartResponse(
        session=session_info,
        opening_narrative=opening,
    )


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str) -> SessionInfo:
    """Get session information."""
    manager = _get_session_manager(session_id)

    return SessionInfo(
        id=session_id,
        campaign_id=manager.campaign.id,
        started_at=datetime.now().isoformat(),  # TODO: Track actual start time
        current_turn=manager.campaign.current_turn,
        is_active=True,
    )


@router.post("/{session_id}/turn", response_model=TurnResponse)
async def process_turn(
    session_id: str,
    request: TurnRequest,
) -> TurnResponse:
    """Process a turn (non-streaming)."""
    manager = _get_session_manager(session_id)

    result = await manager.process_turn(request.player_input)

    # Save after each turn
    manager.save()

    return TurnResponse(
        narrative=result.narrative,
        turn_number=manager.campaign.current_turn,
        bible_updates=[],  # TODO: Track bible updates
        warnings=result.warnings,
    )


@router.post("/{session_id}/save")
async def save_session(session_id: str) -> dict:
    """Save the current session state."""
    manager = _get_session_manager(session_id)
    manager.save()
    return {"message": "Session saved successfully"}


@router.delete("/{session_id}")
async def end_session(session_id: str) -> dict:
    """End and save a session."""
    manager = _get_session_manager(session_id)
    manager.save()
    del _active_sessions[session_id]
    return {"message": "Session ended and saved"}


@router.websocket("/{session_id}/stream")
async def websocket_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for streaming gameplay.

    Messages from client:
    - {"type": "turn", "input": "player action text"}
    - {"type": "ping"}

    Messages to client:
    - {"type": "chunk", "data": {"text": "..."}}
    - {"type": "done", "data": {"turn": N, "tokens_used": N}}
    - {"type": "error", "data": {"message": "..."}}
    - {"type": "bible_update", "data": {"entity_id": "...", "change": "..."}}
    """
    await websocket.accept()

    # Get session manager
    if session_id not in _active_sessions:
        await websocket.send_json(
            WSMessage(
                type=WSMessageType.ERROR,
                data={"message": f"Session '{session_id}' not found"},
            ).model_dump()
        )
        await websocket.close()
        return

    manager = _active_sessions[session_id]

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "turn":
                player_input = data.get("input", "")

                # Send turn start
                await websocket.send_json(
                    WSMessage(
                        type=WSMessageType.TURN_START,
                        data={"turn": manager.campaign.current_turn + 1},
                    ).model_dump()
                )

                # Process the turn
                # TODO: Implement streaming in session manager
                # For now, process and send as chunks
                try:
                    result = await manager.process_turn(player_input)

                    # Simulate streaming by sending in chunks
                    # In production, this would use provider.generate_stream()
                    chunk_size = 50
                    narrative = result.narrative
                    for i in range(0, len(narrative), chunk_size):
                        chunk = narrative[i : i + chunk_size]
                        await websocket.send_json(
                            WSMessage(
                                type=WSMessageType.CHUNK,
                                data={"text": chunk},
                            ).model_dump()
                        )
                        await asyncio.sleep(0.02)  # Small delay for effect

                    # Send done
                    await websocket.send_json(
                        WSMessage(
                            type=WSMessageType.DONE,
                            data={
                                "turn": manager.campaign.current_turn,
                                "tokens_used": 0,  # TODO: Track actual tokens
                            },
                        ).model_dump()
                    )

                    # Save after each turn
                    manager.save()

                except Exception as e:
                    await websocket.send_json(
                        WSMessage(
                            type=WSMessageType.ERROR,
                            data={"message": str(e)},
                        ).model_dump()
                    )

    except WebSocketDisconnect:
        # Client disconnected - save state
        manager.save()
    except Exception as e:
        await websocket.send_json(
            WSMessage(
                type=WSMessageType.ERROR,
                data={"message": f"WebSocket error: {str(e)}"},
            ).model_dump()
        )
