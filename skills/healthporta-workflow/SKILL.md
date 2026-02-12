---
description: Public workflow guidance for HealthPorta MCP operations
alwaysApply: false
---

Use operation-driven discovery and execution when possible.

## Core workflow

1. Discover operations with `find_openapi_operations`.
2. Inspect operation details with `describe_openapi_operation`.
3. Execute with `call_operation`.
4. Use `call_api` only when operation metadata is insufficient.

## Pharmacy query guidance

For pharmacy geo lookups:
- Use `searchPharmaciesByGeo`.
- Combine `name_like` with chain filters.
- Canonical chain keys: `network`, `network_aliases`.
- Accepted MCP aliases in pharmacy context: `chain`, `chain_aliases`.

## Batch guidance

For `call_api_batch` and `call_api_read_batch` request items, either form is supported:
- `{ "method": "GET", "path": "/api/v1/...", "query": {...} }`
- `{ "operation_id": "someOperationId", "query": {...}, "path_params": {...} }`

## Error handling guidance

Tool responses may include:
- `ok=false`
- `error_type`
- `status_code` or `status`
- `summary` or `error`

Interpret these fields directly and avoid retry loops on deterministic `4xx` validation failures.
