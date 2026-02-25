"""
Re-exports all page routers so app/main.py only needs one import.
"""

from app.routes.pages.industry    import router as industry_router
from app.routes.pages.healthcare  import router as healthcare_router
from app.routes.pages.food        import router as food_router
from app.routes.pages.interactive import router as interactive_router
from app.routes.pages.settings    import router as settings_router

all_routers = [
    industry_router,
    healthcare_router,
    food_router,
    interactive_router,
    settings_router,
]
