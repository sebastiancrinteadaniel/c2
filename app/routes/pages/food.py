"""
Food QA - quality assurance page + API.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from pydantic import BaseModel

from app.routes.pages._shared import _render

router = APIRouter()


#  Models 

class MappingEntry(BaseModel):
    product: str
    bin: str

class MappingPayload(BaseModel):
    mapping: list[MappingEntry]


#  Page 

@router.get("/food", response_class=HTMLResponse)
async def food_page(request: Request):
    return _render(request, "food", "pages/food.html")


#  API 

@router.post("/api/food/halt")
async def food_halt():
    """Called when the user presses Halt Production Cycle."""
    print("\n[food] > HALT PRODUCTION CYCLE triggered - TODO: stop conveyor / robot")
    return {"status": "halted"}

@router.post("/api/food/start")
async def food_start(payload: MappingPayload):
    """Called when the user presses Start Task."""
    print("\n" + "="*40)
    print("[food] > START TASK TRIGGERED")
    print("="*40)
    if not payload.mapping:
        print("  (Warning: No products mapped!)")
    else:
        print("  Current product mapping:")
        for e in payload.mapping:
            print(f"    - product={e.product!r:20s}  bin={e.bin}")
    print("="*40 + "\n")
    #  TODO: trigger robot sequence here 
    return {"status": "started"}
