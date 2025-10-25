"""Savezy Expenses API reference."""

# Expenses API

## Authentication

All endpoints require a Google OAuth token. In local testing use an `Authorization` header with the format `Bearer <user_id>|<email>|<name>`.

> **Note:** The production Google OAuth verification layer is maintained separately. Until it lands, the placeholder middleware will return `401` responses in non-test environments.

## Endpoints

### Create Expense
- **Method/Path:** `POST /api/expenses`
- **Body:**
  - `title` *(string, required)*
  - `amount` *(number, required)*
  - `category` *(string, required)*
  - `description` *(string, optional)*
  - `date` *(ISO 8601 datetime, optional)*
- **Response:** `201` with `{ "message": "Expense created successfully.", "data": { "expense": {...} } }`

### List Expenses
- **Method/Path:** `GET /api/expenses`
- **Query Params:**
  - `page` *(int, default 1)*
  - `limit` *(int, default 10, max 100)*
  - `category` *(string, optional)*
  - `sort` *(string, one of: `date`, `amount`, `title`, `category`; default `date`)*
  - `order` *(string, `asc` or `desc`; default `desc`)*
- **Response:** `200` with paginated items in `data.items`.

### Retrieve Expense
- **Method/Path:** `GET /api/expenses/<id>`
- **Response:** `200` with `expense` data or `404` when not found.

### Update Expense
- **Method/Path:** `PUT/PATCH /api/expenses/<id>`
- **Body:** Any subset of fields from creation payload.
- **Response:** `200` with updated `expense` or `404` when not found.

### Delete Expense
- **Method/Path:** `DELETE /api/expenses/<id>`
- **Response:** `200` with `{ "expense_id": <id> }` or `404` if missing.

## Errors
- Validation failures return `400` with details in `data.errors`.
- Missing or invalid authentication returns `401`.
- Not found resources respond with `404`.
