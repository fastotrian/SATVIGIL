import json
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_dir))

from app.main import app

docs_api = Path(__file__).resolve().parents[1] / "docs" / "api"
docs_api.mkdir(parents=True, exist_ok=True)

# 1. Export OpenAPI 3.1 JSON
openapi_schema = app.openapi()
openapi_path = docs_api / "openapi.json"
with open(openapi_path, "w", encoding="utf-8") as f:
    json.dump(openapi_schema, f, indent=2)
print(f"Exported OpenAPI schema to {openapi_path} ({openapi_path.stat().st_size} bytes)")

# 2. Export Postman Collection v2.1
postman_collection = {
    "info": {
        "name": "SATVIGIL API — Maritime & Remote Sensing Intelligence",
        "_postman_id": "satvigil-sih-2026",
        "description": "Production API Collection for SATVIGIL (SIH PS 143 & PS 162)",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": []
}

for path, methods in openapi_schema.get("paths", {}).items():
    for method, details in methods.items():
        if method.lower() not in ("get", "post", "put", "delete", "patch"):
            continue
        summary = details.get("summary") or path
        item = {
            "name": f"{method.upper()} {summary}",
            "request": {
                "method": method.upper(),
                "header": [{"key": "Accept", "value": "application/json"}],
                "url": {
                    "raw": "{{base_url}}" + path,
                    "host": ["{{base_url}}"],
                    "path": [p for p in path.strip("/").split("/") if p]
                },
                "description": details.get("description", "")
            }
        }
        postman_collection["item"].append(item)

postman_path = docs_api / "SATVIGIL_Postman_Collection.json"
with open(postman_path, "w", encoding="utf-8") as f:
    json.dump(postman_collection, f, indent=2)
print(f"Exported Postman Collection with {len(postman_collection['item'])} endpoints to {postman_path}")
