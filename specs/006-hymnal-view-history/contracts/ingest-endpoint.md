# Contract: `POST /api/hymnal-history/events/`

Ingest a batch of hymn view events from the Android app.

- **Auth**: `AllowAny`
- **Throttle**: `ScopedRateThrottle`, scope `hymnal_ingest`, `600/hour` per IP (research R-02)
- **View**: `HymnalHistoryIngestAPI` (`features/songs/views/hymnal_history.py`)
- **URL name**: `hymnal_history_events`

If a valid `Authorization: Bearer <jwt>` is present the events are attributed to that user;
otherwise `user` is stored as null. `device_id` is required either way.

---

## Request

```json
{
  "events": [
    {
      "client_event_id": "5b1f9a4e-1c2d-4f3a-9b8c-7d6e5f4a3b2c",
      "hymn_id": 50,
      "device_id": "9f8e7d6c-5b4a-3928-1706-fedcba987654",
      "viewed_at": "2026-08-09T19:32:11-03:00",
      "duration_seconds": 47,
      "app_version": "1.4.2",
      "platform": "android"
    }
  ]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `events` | array | yes | May be empty. Max length = `max_batch_size` (default 200) |
| `events[].client_event_id` | UUID string | yes | Idempotency key |
| `events[].hymn_id` | integer | yes | `Hymn.id` |
| `events[].device_id` | string ≤ 64 | yes | Required with or without a JWT |
| `events[].viewed_at` | ISO 8601 with offset | yes | When the hymn was viewed, not when it synced |
| `events[].duration_seconds` | integer ≥ 0 | yes | Stored as received; never re-validated |
| `events[].app_version` | string ≤ 32 | no | Defaults to `""` |
| `events[].platform` | string ≤ 32 | no | Defaults to `""` |

`viewed_at` without a UTC offset is rejected as `invalid_event` — a naive timestamp cannot be
placed in a service window without guessing.

---

## Response `201`

```json
{
  "accepted": [
    "5b1f9a4e-1c2d-4f3a-9b8c-7d6e5f4a3b2c",
    "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
  ],
  "rejected": [
    { "client_event_id": "0f0e0d0c-0b0a-4908-8706-050403020100", "reason": "unknown_hymn" }
  ]
}
```

Always `201`, even when every event was rejected — the request itself succeeded. Every submitted
`client_event_id` appears in exactly one of the two lists (FR-013).

**`accepted` = "safe to delete locally"**, covering three different outcomes the app does not need
to distinguish:

| Outcome | Why it is accepted |
|---------|--------------------|
| Stored | The normal case |
| Duplicate — `client_event_id` already exists | The row is already there; re-sending must converge |
| Collapsed — same hymn + device within `collapse_window_minutes` | Deliberately discarded; the view is already represented |

**`rejected`** events are also deleted by the app, with the reason logged. Nothing retries forever.

### Rejection reason codes

| Code | Meaning | Offending value |
|------|---------|-----------------|
| `unknown_hymn` | `hymn_id` does not exist | the `hymn_id` |
| `viewed_at_in_future` | Later than `now + future_tolerance_minutes` | the `viewed_at` |
| `viewed_at_too_old` | Older than `now - max_past_days` | the `viewed_at` |
| `invalid_event` | Malformed event — missing field, bad UUID, naive datetime, negative duration | the field name |

Codes are stable and safe to switch on (research R-07).

---

## Errors

| Status | `error_code` | When |
|--------|--------------|------|
| `400` | `VALIDATION_ERROR` | `events` missing, not a list, or longer than `max_batch_size` |
| `429` | `THROTTLED` | Rate limit exceeded |

Bodies use the project's canonical error shape from `core/http/exceptions.py`:

```json
{ "error_code": "VALIDATION_ERROR", "detail": "Batch of 250 events exceeds max_batch_size of 200." }
```

A batch that is too large fails **as a whole** (FR-010) so the app learns to split. This is the only
condition where one problem affects other events in the request.

---

## Behaviour notes

- **Empty batch** — valid no-op, `201` with two empty lists.
- **Same `client_event_id` twice in one request** — first processed, second treated as duplicate;
  both `accepted`.
- **Intra-batch collapse** — two events for the same hymn and device inside the collapse window are
  collapsed against each other, not only against the database.
- **Duplicate id with different content** — the stored row wins; the incoming payload is discarded.
- **Concurrent identical batches** — the unique constraint absorbs the race; both requests report
  `accepted` (research R-03).
- **`duration_seconds` below `min_seconds_to_count`** — **stored**. That threshold belongs to the
  client and buffered events may carry an older value (FR-011).
