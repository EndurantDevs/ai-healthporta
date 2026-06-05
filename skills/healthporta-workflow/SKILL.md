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

## MRF coverage and import guidance

For client-visible MRF coverage workflows:
- Search public and client-visible sources with `search_mrf_sources`.
- Search discovered group plans with `search_group_plans`.
- Submit a payer or employer MRF index/TOC URL with `submit_mrf_index_source`.
- Subscribe to a discovered group plan with `subscribe_group_plan`.
- Track import work with `list_import_requests`, `get_import_request_status`, and `cancel_import_request`.
- Start an explicit PTG import request with `start_import_request` only when the user asks to queue import work.

For admin import orchestration, use admin tools such as `list_imports`,
`fetch_group_plan_catalog`, `resolve_group_plan_imports`, `dispatch_group_plan_imports`,
and `replicate_group_plan_import` only when the authenticated session has admin import-control access.

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
