"""Savezy Expenses and Cards API reference."""

# Expenses API

## Interactive Documentation

- **Swagger UI:** Visit [`/docs`](http://localhost:5000/docs) when the server is running to explore and test endpoints.
- **OpenAPI Spec:** The raw OpenAPI document is served at [`/openapi.yaml`](http://localhost:5000/openapi.yaml).

## Authentication

All endpoints require a Google OAuth token. In local testing use an `Authorization` header with the format `Bearer <user_id>|<email>|<name>`.

> **Note:** The production Google OAuth verification layer is maintained separately. Until it lands, the placeholder middleware will return `401` responses in non-test environments.

## Endpoints

### Create Expense
- **Method/Path:** `POST /api/expenses`
- **Body:**
  - `title` *(string, required)*
  - `amount` *(number, required)*
  - `category` *(string, required; enum: `investment`, `wants`, `need`)*
  - `type` *(string, required; enum: `investment`, `wants`, `need`)*
  - `card_id` *(integer, required; references saved card)*
  - `description` *(string, optional)*
  - `date` *(ISO 8601 datetime, optional)*
- **Response:** `201` with `{ "message": "Expense created successfully.", "data": { "expense": {...} } }`
  - `expense.category` is the stored slug; `expense.category_name` is the human-readable name.
  - `expense.type` reflects the high-level classification (`wants`, `need`, `investment`).
  - `expense.card` contains the linked card object (including type-specific fields).

### List Expenses
- **Method/Path:** `GET /api/expenses`
- **Query Params:**
  - `page` *(int, default 1)*
  - `limit` *(int, default 10, max 100)*
  - `category` *(string, optional; enum: `investment`, `wants`, `need`)*
  - `type` *(string, optional; enum: `investment`, `wants`, `need`)*
  - `sort` *(string, one of: `date`, `amount`, `title`, `category`, `type`; default `date`)*
  - `order` *(string, `asc` or `desc`; default `desc`)*
- **Response:** `200` with paginated items in `data.items`.
  - Each item includes both `category` (slug) and `category_name`.
  - Each item includes the `type` field and the nested `card` object.

### Retrieve Expense
- **Method/Path:** `GET /api/expenses/<id>`
- **Response:** `200` with `expense` data or `404` when not found.

### Update Expense
- **Method/Path:** `PUT/PATCH /api/expenses/<id>`
- **Body:** Any subset of fields from creation payload (type/category updates must use valid enums).
- **Response:** `200` with updated `expense` or `404` when not found.

### Delete Expense
- **Method/Path:** `DELETE /api/expenses/<id>`
- **Response:** `200` with `{ "expense_id": <id> }` or `404` if missing.

# Cards API

### Create Card
- **Method/Path:** `POST /api/cards`
- **Body (minimum fields):**
  - `name` *(string, required)*
  - `type` *(string, required; enum: `credit`, `debit`, `prepaid`)*
  - `limit` *(number, required when `type=credit`)*
  - `total_balance` & `balance_left` *(numbers, required when `type=prepaid`; `balance_left <= total_balance`)*
  - Optional fields: `apple_slug`, `brand`, `last_four`
- **Response:** `201` with `{ "card": {...} }`

### List Cards
- **Method/Path:** `GET /api/cards`
- **Query Params:**
  - `page` *(int, default 1)*
  - `limit` *(int, default 10, max 100)*
  - `type` *(string, optional; enum: `credit`, `debit`, `prepaid`)*
  - `sort` *(string, default `created`; accepted: `created`, `name`, `type`, `limit`, `total_balance`, `balance_left`)*
  - `order` *(string, `asc` or `desc`; default `desc`)*
- **Response:** `200` with paginated `items`, each containing the serialized card object.
  - Each item includes `last_four` but omits `brand` (fetch a single card for full metadata).

### Retrieve Card
- **Method/Path:** `GET /api/cards/<id>`
- **Response:** `200` with `{ "card": {...} }` or `404` if not found.

### Update Card
- **Method/Path:** `PUT/PATCH /api/cards/<id>`
- **Body:** Any subset of card fields. Type transitions enforce the same validation rules as creation.
- **Response:** `200` with updated card or `400`/`404` on validation/not-found issues.

### Delete Card
- **Method/Path:** `DELETE /api/cards/<id>`
- **Response:** `200` with `{ "card_id": <id> }` when deletion succeeds.
- **Constraint:** Cards referenced by expenses respond with `409` until dependent expenses are removed.

## Errors
- Validation failures return `400` with details in `data.errors`.
- Missing or invalid authentication returns `401`.
- Not found resources respond with `404`.
- Deleting a card that still has expenses returns `409`.
