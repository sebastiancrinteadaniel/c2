"""
Page routes — one GET per sidebar item.
Each renders its template with active_page so the sidebar can highlight
the correct nav item.

Also contains lightweight page-specific REST endpoints.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _render(request: Request, page: str, template: str, **ctx):
    return templates.TemplateResponse(
        template,
        {"request": request, "active_page": page, **ctx},
    )


# ── Page routes ────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def industry(request: Request):
    return _render(request, "industry", "pages/industry.html")


@router.get("/healthcare", response_class=HTMLResponse)
async def healthcare(request: Request):
    return _render(request, "healthcare", "pages/healthcare.html")


@router.get("/food", response_class=HTMLResponse)
async def food(request: Request):
    return _render(request, "food", "pages/food.html")


@router.get("/interactive", response_class=HTMLResponse)
async def interactive(request: Request):
    return _render(request, "interactive", "pages/interactive.html")


@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    return _render(request, "settings", "pages/settings.html")


# ── Industry 5.0 API ───────────────────────────────────────────────────────

class MappingEntry(BaseModel):
    part: str
    bin: int

class MappingPayload(BaseModel):
    mapping: list[MappingEntry]


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
