"""
Healthcare - RX verification page + API.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.routes.pages._shared import _render

router = APIRouter()


#  Page 

@router.get("/healthcare", response_class=HTMLResponse)
async def healthcare_page(request: Request):
    return _render(request, "healthcare", "pages/healthcare.html")


class HealthcareStart(BaseModel):
    injection_length: int

#  API 

@router.post("/api/healthcare/inspect")
async def healthcare_inspect():
    """Called when the user presses Inspect on an RX document."""
    print("\n[healthcare] > INSPECT triggered - TODO: run OCR / text detection on RX doc")
    return {"status": "inspect_started"}

@router.post("/api/healthcare/start")
async def healthcare_start(payload: HealthcareStart):
    """Called when the user presses Start Task."""
    print("\n" + "="*40)
    print("[healthcare] > START TASK TRIGGERED")
    print("="*40)
    print(f"  Injection Length: {payload.injection_length}mm")
    print("="*40 + "\n")
    #  TODO: trigger robot injection sequence 
    return {"status": "started"}
