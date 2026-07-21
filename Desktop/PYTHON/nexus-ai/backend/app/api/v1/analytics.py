"""
Analytics API — Superset embedding support.

GET /api/v1/analytics/dashboards
  Returns the three pre-provisioned dashboard UUIDs and metadata.

GET /api/v1/analytics/embed-token?dashboard_id={uuid}
  Exchanges admin credentials for a short-lived Superset guest token.
  The frontend never holds Superset admin credentials.
"""
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.auth import get_current_user
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# ─── Dashboard registry ───────────────────────────────────────────────────────
# These UUIDs are set during Superset setup (setup_dashboards.py).
# They're stable across container restarts because the setup script passes
# them explicitly when creating each dashboard.
DASHBOARDS = [
    {
        "id": settings.SUPERSET_DASH_EXEC_UUID,
        "slug": "exec-overview",
        "name": "Executive Overview",
        "description": "Total revenue, revenue trend, and top regions at a glance.",
    },
    {
        "id": settings.SUPERSET_DASH_SALES_UUID,
        "slug": "sales-deep-dive",
        "name": "Sales Deep Dive",
        "description": "Actuals vs. forecast overlay by region and product.",
    },
    {
        "id": settings.SUPERSET_DASH_ANOMALY_UUID,
        "slug": "anomaly-monitor",
        "name": "Anomaly & Ops Monitor",
        "description": "Flagged anomalies over time, pipeline job status, and model scores.",
    },
]

_VALID_IDS = {d["id"] for d in DASHBOARDS} | {d["slug"] for d in DASHBOARDS}


# ─── Superset client helpers ──────────────────────────────────────────────────

async def _superset_access_token() -> str:
    """Authenticate to Superset and return a short-lived access token."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{settings.SUPERSET_URL}/api/v1/security/login",
            json={
                "username": settings.SUPERSET_ADMIN_USERNAME,
                "password": settings.SUPERSET_ADMIN_PASSWORD,
                "provider": "db",
                "refresh": True,
            },
        )
    if resp.status_code != 200:
        logger.error("Superset login failed: %s", resp.text[:300])
        raise HTTPException(503, "Analytics service unavailable — login failed")
    return resp.json()["access_token"]


async def _get_guest_token(dashboard_id: str, access_token: str) -> str:
    """Exchange an admin access token for a guest token for one dashboard."""
    # Resolve slug → UUID if needed
    resolved_id = dashboard_id
    for d in DASHBOARDS:
        if dashboard_id == d["slug"]:
            resolved_id = d["id"]
            break

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{settings.SUPERSET_URL}/api/v1/security/guest_token/",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "user": {
                    "username": "nexus_guest",
                    "first_name": "NEXUS",
                    "last_name": "Guest",
                },
                "resources": [{"type": "dashboard", "id": resolved_id}],
                "rls": [],  # row-level security rules (none = full read access)
            },
        )
    if resp.status_code != 200:
        logger.error("Guest token request failed: %s", resp.text[:300])
        raise HTTPException(503, "Analytics service unavailable — guest token failed")
    return resp.json()["token"]


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/dashboards", summary="List available Superset dashboards")
def list_dashboards(current_user: User = Depends(get_current_user)):
    """Returns dashboard metadata including UUIDs and Superset embed URL base."""
    return {
        "superset_url": settings.SUPERSET_URL,
        "dashboards": DASHBOARDS,
    }


@router.get("/embed-token", summary="Get a Superset guest token for dashboard embedding")
async def get_embed_token(
    dashboard_id: str = Query(
        ...,
        description="Dashboard UUID or slug (exec-overview, sales-deep-dive, anomaly-monitor)",
    ),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a short-lived Superset guest token.
    The frontend uses this token to render a dashboard inside an iframe without
    exposing admin credentials to the browser.

    Token lifespan: 5 minutes (Superset default).
    """
    if dashboard_id not in _VALID_IDS:
        raise HTTPException(
            400,
            detail=f"Unknown dashboard_id '{dashboard_id}'. "
                   f"Valid values: {sorted(_VALID_IDS)}",
        )

    try:
        access_token = await _superset_access_token()
        guest_token = await _get_guest_token(dashboard_id, access_token)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error getting embed token")
        raise HTTPException(503, f"Analytics service error: {exc}") from exc

    # Resolve to UUID for the iframe URL
    resolved_uuid = dashboard_id
    for d in DASHBOARDS:
        if dashboard_id in (d["slug"], d["id"]):
            resolved_uuid = d["id"]
            break

    return {
        "token": guest_token,
        "dashboard_id": resolved_uuid,
        "expires_in": 300,
        "embed_url": (
            f"{settings.SUPERSET_URL}/superset/dashboard"
            f"/{resolved_uuid}/?standalone=3"
        ),
    }


# ─── Internal embed-token (used by the Next.js API route, no JWT) ────────────

from typing import Optional as Opt
from fastapi import Header as FHeader

@router.get(
    "/internal/embed-token",
    summary="Internal: get embed token without JWT (uses x-internal-secret)",
    include_in_schema=False,  # hide from public OpenAPI docs
)
async def internal_embed_token(
    dashboard_id: str = Query(...),
    x_internal_secret: Opt[str] = FHeader(None),
):
    if x_internal_secret != settings.N8N_WEBHOOK_SECRET:
        raise HTTPException(401, "Unauthorized")
    if dashboard_id not in _VALID_IDS:
        raise HTTPException(400, f"Unknown dashboard_id '{dashboard_id}'")

    try:
        access_token = await _superset_access_token()
        guest_token = await _get_guest_token(dashboard_id, access_token)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"Analytics service error: {exc}") from exc

    resolved_uuid = dashboard_id
    for d in DASHBOARDS:
        if dashboard_id in (d["slug"], d["id"]):
            resolved_uuid = d["id"]
            break

    return {
        "token": guest_token,
        "dashboard_id": resolved_uuid,
        "expires_in": 300,
        "embed_url": f"{settings.SUPERSET_URL}/superset/dashboard/{resolved_uuid}/?standalone=3",
    }
