"""Minimal, dependency-free JSON-Schema validator.

Supports exactly the subset used by the integration contracts:
    type (object/array/string/number/integer/boolean/null, or a list of types),
    required, properties, additionalProperties (bool), enum, const, items,
    minItems / maxItems, minimum / maximum.

This is intentionally small and explicit rather than pulling in `jsonschema`,
so the integration package stays lightweight and auditable. It raises
`SchemaError` with a JSON-path-ish location on the first violation.
"""
from __future__ import annotations

from typing import Any

_TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


class SchemaError(ValueError):
    """Raised when an instance does not satisfy a schema."""


def _type_ok(value: Any, t: str) -> bool:
    if t == "number":
        # bool is a subclass of int in Python; exclude it from numbers.
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, _TYPE_MAP[t])


def _check(value: Any, schema: dict, path: str) -> None:
    # type
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_type_ok(value, tt) for tt in types):
            raise SchemaError(f"{path}: expected type {t}, got {type(value).__name__}")

    # const
    if "const" in schema and value != schema["const"]:
        raise SchemaError(f"{path}: must equal const {schema['const']!r}, got {value!r}")

    # enum
    if "enum" in schema and value not in schema["enum"]:
        raise SchemaError(f"{path}: {value!r} not in enum {schema['enum']}")

    # numeric bounds
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise SchemaError(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise SchemaError(f"{path}: {value} > maximum {schema['maximum']}")

    # object
    if isinstance(value, dict) and (schema.get("type") == "object" or "properties" in schema):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                raise SchemaError(f"{path}: missing required property '{req}'")
        if schema.get("additionalProperties") is False:
            extra = set(value) - set(props)
            if extra:
                raise SchemaError(f"{path}: unexpected properties {sorted(extra)}")
        for key, subschema in props.items():
            if key in value:
                _check(value[key], subschema, f"{path}.{key}")

    # array
    if isinstance(value, list) and (schema.get("type") == "array" or "items" in schema):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise SchemaError(f"{path}: array shorter than minItems {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise SchemaError(f"{path}: array longer than maxItems {schema['maxItems']}")
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(value):
                _check(item, item_schema, f"{path}[{i}]")


def validate(instance: Any, schema: dict) -> None:
    """Validate `instance` against `schema`; raise SchemaError on the first
    violation. Returns None on success."""
    _check(instance, schema, path="$")
