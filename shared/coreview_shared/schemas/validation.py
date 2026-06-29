"""Validate Pydantic models against bundled JSON Schema artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
from pydantic import BaseModel

_SCHEMAS_DIR = Path(__file__).resolve().parent


def _load_schema(name: str) -> dict[str, Any]:
    path = _SCHEMAS_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def validate_against_schema(model: BaseModel, schema_filename: str) -> None:
    schema = _load_schema(schema_filename)
    payload = json.loads(model.model_dump_json(exclude_none=True))
    jsonschema.validate(instance=payload, schema=schema)


REVIEW_EXECUTION_REQUEST_SCHEMA = "review-execution-request-v1.schema.json"
KUBERNETES_EXECUTION_SPEC_SCHEMA = "kubernetes-execution-spec-v1.schema.json"
COGITO_REVIEW_RUN_SCHEMA = "cogito-review-run-v1.schema.json"
