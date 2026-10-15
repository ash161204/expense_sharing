# API Reference

Interactive version: **`/api/docs`** (Swagger UI). OpenAPI schema: `/api/schema`.

## Conventions

| Topic | Rule |
|---|---|
| URLs | start with `/api/`, no trailing slash |
| Body | JSON |
| Money in requests | rupees as a string or number (`"1200.50"` or `1200.5`); must be > 0 with at most 2 decimals |
| Money in responses | a string with 2 decimals (`"400.00"`, `"-1466.67"`) |
| Errors | **400** when the request is invalid (the response names the field), **404** when the group in the URL doesn't exist |

```json
{"payers": ["Users [7] are not members of this group."]}
{"non_field_errors": ["You cannot settle with yourself."]}
{"detail": "No Group matches the given query."}
```

## Users

**`POST /api/users`** `{"name": "Mohit"}` → **201** `{"id": 1, "name": "Mohit", "created_at": "..."}`
400 if the name is blank, longer than 100 characters, or already taken (ignoring case).

**`GET /api/users`** → **200** a list of users.

## Groups

**`POST /api/groups`** `{"name": "Goa Trip"}` → **201** `{"id": 1, "name": "Goa Trip", "created_at": "..."}`
**`GET /api/groups`** → a list of groups. **`GET /api/groups/{id}`** → one group, or 404.

## Members

**`POST /api/groups/{id}/members`** `{"user_id": 2}` → **201** the user.
400 if the user doesn't exist or is already a member; 404 if the group doesn't exist.

**`GET /api/groups/{id}/members`** → **200** a list of users.

## Expenses

**`POST /api/groups/{id}/expenses`**

Equal split (all members by default; `participant_ids` limits it to some members):
```json
{"description": "Dinner", "amount": "1200", "payers": [{"user_id": 1, "amount": "1200"}]}
```

Item split, with one or more payers:
```json
{
  "description": "Hotel",
  "amount": "9000",
  "payers": [{"user_id": 1, "amount": "6000"}, {"user_id": 3, "amount": "3000"}],
  "split_type": "itemized",
  "items": [
    {"name": "Room A", "amount": "5000", "shared_by": [1, 2]},
    {"name": "Room B", "amount": "4000", "shared_by": [3]}
  ]
}
```

**Validation (400):**
- Amounts are > 0 with at most 2 decimals.
- There is at least one payer; payers are group members, listed once each, and **add up to `amount`**.
- **Equal split:** participants are group members listed once each, and the amount gives everyone at least ₹0.01.
- **Itemized:** there is at least one item; items **add up to `amount`**; each `shared_by` lists group members once each; each item gives everyone at least ₹0.01.

**What's saved (in one transaction):** the expense, one payment row per payer, the items and item shares (itemized only), and one split row per person.

**201 response:**
```json
{
  "id": 1,
  "description": "Hotel",
  "amount": "9000.00",
  "split_type": "itemized",
  "payers": [{"user_id": 1, "name": "Mohit", "amount": "6000.00"}, {"user_id": 3, "name": "Ankit", "amount": "3000.00"}],
  "splits": [
    {"user_id": 1, "name": "Mohit", "amount": "2500.00"},
    {"user_id": 2, "name": "Rahul", "amount": "2500.00"},
    {"user_id": 3, "name": "Ankit", "amount": "4000.00"}
  ],
  "items": [
    {"name": "Room A", "amount": "5000.00", "shared_by": [
      {"user_id": 1, "name": "Mohit", "amount": "2500.00"}, {"user_id": 2, "name": "Rahul", "amount": "2500.00"}]},
    {"name": "Room B", "amount": "4000.00", "shared_by": [{"user_id": 3, "name": "Ankit", "amount": "4000.00"}]}
  ],
  "created_at": "2026-10-14T10:30:00Z"
}
```
For an equal split, `items` is `[]`. When an amount doesn't divide evenly, the leftover paisa goes to the lowest user id (₹100 / 3 = 33.34, 33.33, 33.33).

**`GET /api/groups/{id}/expenses`** → **200** expense history, newest first (same shape as above).

## Balances

**`GET /api/groups/{id}/balances`**
```json
{
  "members": [
    {"user_id": 1, "name": "Mohit", "paid": "1200.00", "share": "400.00", "net": "800.00"},
    {"user_id": 2, "name": "Rahul", "paid": "0.00", "share": "400.00", "net": "-400.00"},
    {"user_id": 3, "name": "Ankit", "paid": "0.00", "share": "400.00", "net": "-400.00"}
  ],
  "owes": {
    "Rahul": {"owes": {"Mohit": "400.00"}},
    "Ankit": {"owes": {"Mohit": "400.00"}}
  }
}
```
`net = paid − share + settlements sent − settlements received`. `owes` is a short list of payments that settles everyone (at most n − 1 payments for n members).

## Settlements

**`POST /api/groups/{id}/settlements`** `{"from_user_id": 2, "to_user_id": 1, "amount": "400"}` → **201**
```json
{"id": 1, "from_user_id": 2, "from_user": "Rahul", "to_user_id": 1, "to_user": "Mohit", "amount": "400.00", "created_at": "..."}
```
400 if:
- the two users are the same person
- either user isn't a group member
- the amount is more than `min(what the sender owes, what the receiver is owed)`, e.g. `{"amount": ["You can settle at most 400.00 here."]}`

The check and the insert run in one transaction.

**`GET /api/groups/{id}/settlements`** → **200** settlement history, newest first.

## PDF export

**`GET /api/groups/{id}/pdf`** → **200** a PDF download (`Content-Disposition: attachment; filename="goa-trip.pdf"`) with the group's balances, who pays whom, expense history and settlements. 404 if the group doesn't exist.

## Login

**`POST /api/auth/signup`** `{"name": "Mohit", "password": "secret1"}` → **201** `{"token": "...", "user": {"id": 1, "name": "Mohit", ...}}`
400 if the name is already taken by someone with an account. A name that a friend added (no password yet) can be claimed this way.

**`POST /api/auth/login`** (same body) → **200** `{"token": "...", "user": {...}}`, or 400 `Wrong name or password.`

**`GET /api/auth/me`** → **200** the logged-in user, or 401.

Send the token as `Authorization: Bearer <token>` (in Swagger: the **Authorize** button). The token is the user id signed with the server's secret key, valid for 30 days. The core endpoints above don't require it. The assistant endpoints below do.

## AI assistant (login required)

**`POST /api/groups/{id}/assistant`**: one chat turn. The browser sends back the draft from the previous turn.
```json
{"draft": null, "message": "I paid 1200 for dinner, split between everyone", "question": ""}
```
**200**, when something is still missing:
```json
{"draft": {"description": "Beach shack lunch", "amount": "", "payers": [], "items": [...], "participant_ids": [1, 2, 3]},
 "question": "Who paid?", "errors": {}, "shares": []}
```
**200**, when the draft is complete (`question` is null):
```json
{"draft": {"description": "Dinner", "amount": "1200", "payers": [{"user_id": 1, "amount": "1200"}],
           "participant_ids": [1, 2, 3], "split_type": "equal"},
 "question": null, "errors": {},
 "shares": [{"user_id": 1, "name": "Mohit", "amount": "400.00"}, {"user_id": 2, "name": "Rahul", "amount": "400.00"},
            {"user_id": 3, "name": "Ankit", "amount": "400.00"}]}
```
To save it, send `draft` to `POST /api/groups/{id}/expenses` unchanged. If the draft breaks a rule, `errors` holds the same messages the expenses endpoint would give.

Questions are asked in this order, and only when needed:
1. "What did you spend on?"
2. (receipts only) "The items add up to X but the receipt's subtotal is Y"
3. "Who had what?"
4. "Who paid?"
5. "How much did each person pay?" (2+ payers)
6. "What should we call this expense?"

Errors:
- 400 if you're not a member of the group, or `Sorry, I couldn't understand that…` if the model's answer didn't fit the schema.
- 401 if you're not logged in.
- 503 if the free AI quota is used up or Groq is unreachable. The rest of the app keeps working.

Amounts: the model writes "a thousand" as `1000`. "X paid the rest" becomes `rest`, which the server turns into total − what the others paid.

**`POST /api/assistant/scan`** (multipart, field `image`) → **200** `{"text": "Scanned receipt of a bill our group shared:\nPUMPKIN VANILLA 165.00V\n..."}`. Send `text` as the next chat message. The OCR runs locally on the server. 400 if the file isn't an image.

**`POST /api/groups/{id}/assistant/transcribe`** (multipart, field `audio`, e.g. webm or wav) → **200** `{"text": "I paid a thousand, and the remaining was paid by Ankit."}`. The group's names are given to Whisper as a spelling hint. 503 if Groq is unavailable.
