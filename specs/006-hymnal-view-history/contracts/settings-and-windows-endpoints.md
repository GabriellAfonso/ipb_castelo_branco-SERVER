# Contract: Settings & Service Windows Endpoints

Administration surface for the collection behaviour. The settings **read** is the only one open
without credentials — the app needs `min_seconds_to_count` on a fresh install before anyone logs in.

---

## `GET /api/hymnal-history/settings/`

- **Auth**: `AllowAny` · **View**: `HymnalHistorySettingsAPI` · **URL name**: `hymnal_history_settings`

### Response `200`

```json
{
  "min_seconds_to_count": 30,
  "collapse_window_minutes": 10,
  "max_batch_size": 200,
  "max_past_days": 90,
  "future_tolerance_minutes": 5,
  "window_grace_minutes": 30
}
```

Plain numbers, no sensitive content. On a database that has never been written to, the defaults
above are materialised on first read (research R-06), so this endpoint never 404s.

**The app must tolerate this being unreachable** at startup by falling back to its last known values
or a built-in 30-second default. That is app-side behaviour; the backend guarantees only that the
values are readable without credentials.

---

## `PATCH /api/hymnal-history/settings/`

- **Auth**: `IsAdminUser` · same view, same URL

### Request

Partial — send only what changes.

```json
{ "min_seconds_to_count": 45 }
```

### Validation (FR-026)

Every field a positive whole number within its bound:

| Field | Min | Max |
|-------|-----|-----|
| `min_seconds_to_count` | 1 | 3600 |
| `collapse_window_minutes` | 1 | 1440 |
| `max_batch_size` | 1 | 1000 |
| `max_past_days` | 1 | 3650 |
| `future_tolerance_minutes` | 1 | 1440 |
| `window_grace_minutes` | 1 | 1440 |

### Response `200`

The full updated settings object, same shape as the `GET`.

### Errors

| Status | `error_code` | When |
|--------|--------------|------|
| `400` | `VALIDATION_ERROR` | Any field zero, negative, non-integer, or above its maximum |
| `401` / `403` | `NOT_AUTHENTICATED` / `PERMISSION_DENIED` | Not an admin |

Error bodies carry `field_errors` naming the field, the offending value and the accepted range:

```json
{
  "error_code": "VALIDATION_ERROR",
  "detail": "Validation failed.",
  "field_errors": {
    "min_seconds_to_count": ["Value 0 is out of range. Expected an integer between 1 and 3600."]
  }
}
```

### Effect

**Future behaviour only** (FR-027). No stored event is rewritten, re-evaluated or deleted. Events
collected under an older threshold stay exactly as they are — including events whose duration is
below a newly raised `min_seconds_to_count`.

Note that `collapse_window_minutes` affects *ingest only*. Occurrence collapsing at read time uses
service windows, not this value, so changing it never alters an existing report.

`window_grace_minutes` is the opposite: it applies at **read time**, so changing it re-interprets
history that is already stored. A hymn recorded at 21:20 moves in or out of Culto Dominical
depending on the current value. No stored event changes — only how it is read.

---

## `GET /api/hymnal-history/service-windows/`

- **Auth**: `IsAdminUser` · **View**: `ServiceWindowListCreateAPI` · **URL name**: `service_windows`

### Response `200`

```json
{
  "service_windows": [
    { "id": 3, "name": "Culto de Domingo à Noite", "weekday": 6, "start_time": "19:00:00", "end_time": "21:00:00", "active": true }
  ]
}
```

Ordered by `weekday`, then `start_time` — the same ordering that decides which window wins when two
overlap (FR-016).

**`weekday` is `0 = Monday … 6 = Sunday`** (Python's `datetime.weekday()`). Sunday is `6`, not `0`.

---

## `POST /api/hymnal-history/service-windows/`

- **Auth**: `IsAdminUser` · same view

### Request

```json
{ "name": "Culto de Oração", "weekday": 2, "start_time": "19:30", "end_time": "21:00", "active": true }
```

`active` is optional and defaults to `true`. Everything else is required.

### Response `201`

The created window, same shape as a list entry.

### Validation

| Rule | Message shape |
|------|---------------|
| `end_time` strictly after `start_time` | names both values |
| `weekday` in 0–6 | names the offending value and the range |
| `name` non-empty, ≤ 100 chars | |

Enforced at the serializer **and** by database check constraints (`data-model.md`), so neither the
admin site nor a shell session can create an invalid window.

---

## `GET` / `PATCH` / `DELETE /api/hymnal-history/service-windows/{id}/`

- **Auth**: `IsAdminUser` · **View**: `ServiceWindowDetailAPI` · **URL name**: `service_window_detail`

| Method | Response | Notes |
|--------|----------|-------|
| `GET` | `200` with the window | |
| `PATCH` | `200` with the updated window | Partial; same validation as create |
| `DELETE` | `204`, empty body | |

`404` with `error_code: "NOT_FOUND"` when the id does not exist, raised as a domain
`NotFoundError` from the service and mapped by `core/http/exceptions.py`.

### Effect on history

Creating, editing, deactivating or deleting a window **never touches a stored event** (FR-023).
Occurrences are derived at read time, so the next report simply reflects the new configuration.
Deleting a window that past occurrences were grouped under makes those events regroup by calendar
day — the history is intact, only the interpretation changed.

Deactivating (`active: false`) is the gentler option and is preferred over deleting when a service
merely stops happening: the row stays available to be turned back on.
