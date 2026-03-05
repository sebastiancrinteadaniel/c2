from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.services.global_settings import get_end_effector_status_text

templates = Jinja2Templates(directory="app/templates")


def _render(request: Request, page: str, template: str, **ctx):
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "active_page": page,
            "end_effector_status_text": get_end_effector_status_text(),
            **ctx,
        },
    )
