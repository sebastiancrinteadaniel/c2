"""
Food QA — quality assurance page + API.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.routes.pages._shared import _render

router = APIRouter()


# ── Page ──────────────────────────────────────────────────────────────────

@router.get("/food", response_class=HTMLResponse)
async def food_page(request: Request):
    return _render(request, "food", "pages/food.html")


# ── API ───────────────────────────────────────────────────────────────────

@router.post("/api/food/halt")
async def food_halt():
    """Called when the user presses Halt Production Cycle."""
    print("\n[food] ▶ HALT PRODUCTION CYCLE triggered — TODO: stop conveyor / robot")
    return {"status": "halted"}
