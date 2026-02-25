from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


def _render(request: Request, page: str, template: str, **ctx):
    return templates.TemplateResponse(
        template,
        {"request": request, "active_page": page, **ctx},
    )
