"""ASGI entrypoint for the Advay FastAPI app."""

from advay_platform.api import create_app

app = create_app()
