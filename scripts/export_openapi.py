"""Export the FastAPI OpenAPI spec as JSON to stdout."""

import json

from app.main import app

spec = app.openapi()
print(json.dumps(spec, indent=2))
