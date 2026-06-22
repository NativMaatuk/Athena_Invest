from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_active_users_service
from ..schemas import ActiveUsersHeartbeatRequest, ActiveUsersResponse
from ..services.active_users_service import ActiveUsersService

router = APIRouter(prefix="/api/v1/presence", tags=["presence"])


@router.post("/heartbeat", response_model=ActiveUsersResponse)
async def heartbeat(
    payload: ActiveUsersHeartbeatRequest,
    service: ActiveUsersService = Depends(get_active_users_service),
) -> ActiveUsersResponse:
    return ActiveUsersResponse(
        active_users=service.touch(payload.session_id),
        window_seconds=service.window_seconds,
    )


@router.get("/active-users", response_model=ActiveUsersResponse)
async def active_users(
    service: ActiveUsersService = Depends(get_active_users_service),
) -> ActiveUsersResponse:
    return ActiveUsersResponse(
        active_users=service.active_count(),
        window_seconds=service.window_seconds,
    )
