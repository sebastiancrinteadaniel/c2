"""
Industry 5.0 — sorting page + API.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.routes.pages._shared import _render

router = APIRouter()


# ── Page ──────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def industry_page(request: Request):
    return _render(request, "industry", "pages/industry.html")


# ── Models ────────────────────────────────────────────────────────────────

class MappingEntry(BaseModel):
    part: str
    bin: int

class MappingPayload(BaseModel):
    mapping: list[MappingEntry]


# ── API ───────────────────────────────────────────────────────────────────

@router.post("/api/industry/mapping")
async def industry_mapping(payload: MappingPayload):
    """Called whenever the user changes a part→bin row."""
    print("\n[industry] Mapping updated:")
    for e in payload.mapping:
        print(f"  part={e.part!r:20s}  bin={e.bin}")
    return {"status": "ok"}


@router.post("/api/industry/start")
async def industry_start(payload: MappingPayload):
    """Called when the user presses Start Task."""
    print("\n[industry] ▶ START TASK — current mapping:")
    for e in payload.mapping:
        print(f"  part={e.part!r:20s}  bin={e.bin}")
    # TODO: trigger robot sequence here
    return {"status": "started"}
