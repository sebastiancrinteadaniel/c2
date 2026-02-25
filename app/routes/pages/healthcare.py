"""
Healthcare — RX verification page + API.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.routes.pages._shared import _render

router = APIRouter()


# ── Page ──────────────────────────────────────────────────────────────────

@router.get("/healthcare", response_class=HTMLResponse)
async def healthcare_page(request: Request):
    return _render(request, "healthcare", "pages/healthcare.html")


# ── API ───────────────────────────────────────────────────────────────────

@router.post("/api/healthcare/inspect")
async def healthcare_inspect():
    """Called when the user presses Inspect on an RX document."""
    print("\n[healthcare] ▶ INSPECT triggered — TODO: run OCR / text detection on RX doc")
    return {"status": "inspect_started"}
