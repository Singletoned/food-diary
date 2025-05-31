import os
import pypugjs
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

# Determine the project's base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Ensure the static directory exists, as Starlette expects it
os.makedirs(STATIC_DIR, exist_ok=True)


def render_pug_template(template_name: str, context: dict = None) -> HTMLResponse:
    """
    Renders a Pug template to an HTMLResponse.
    """
    if context is None:
        context = {}

    template_path = os.path.join(TEMPLATES_DIR, template_name)

    # pypugjs.simple_convert expects the Pug source code as a string
    with open(template_path, "r") as f:
        pug_source = f.read()

    # pypugjs compiler options can be passed here if needed
    # For example, to use a specific Jinja2 environment or filters
    # compiler = pypugjs.Compiler(source=pug_source, ...)
    # html = compiler.compile()
    # For simplicity, using simple_convert which uses default compiler settings
    html_content = pypugjs.simple_convert(pug_source)

    return HTMLResponse(html_content)


async def homepage(request):
    """
    Serves the homepage by rendering the index.pug template.
    """
    return render_pug_template("index.pug", {"request": request})


routes = [
    Route("/", homepage),
    Mount("/static", app=StaticFiles(directory=STATIC_DIR), name="static"),
]

app = Starlette(debug=True, routes=routes)
