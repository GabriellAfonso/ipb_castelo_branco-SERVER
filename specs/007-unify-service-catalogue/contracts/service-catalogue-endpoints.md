# Contract: Service Catalogue Endpoints

The service-window endpoints from feature 006 keep their paths and shapes, and now manage the
**shared catalogue** instead of the hymnal's private copy (FR-013). Two fields are added and one
delete becomes protected.

Paths are unchanged so the Android app needs no release. The name "service-windows" in the URL is
now slightly historical; renaming it would be an API break for cosmetic gain.

---

## `GET /api/hymnal-history/service-windows/`

- **Auth**: `IsAdminUser` · **View**: `ServiceWindowListCreateAPI`

### Response `200`

```json
{
  "service_windows": [
    {
      "id": 3,
      "name": "Domingo Liturgia de Adoração",
      "weekday": 1,
      "start_time": "19:30:00",
      "end_time": "21:00:00",
      "active": true,
      "takes_rota": true
    },
    {
      "id": 4,
      "name": "Escola Bíblica Dominical",
      "weekday": 1,
      "start_time": "09:00:00",
      "end_time": "10:00:00",
      "active": true,
      "takes_rota": false
    }
  ]
}
```

### ⚠️ `weekday` changes meaning

**Before**: `0 = Monday … 6 = Sunday` — Sunday was `6`.
**After**: `1 = Sunday … 7 = Saturday` — Sunday is `1`.

This is the one field whose *interpretation* changes. It is safe because the endpoint has never been
deployed and no client reads it yet — but it must be stated loudly, because the values overlap: a
`weekday` of `3` is valid under both conventions and means Thursday under one and Tuesday under the
other.

The convention now matches the rota's, which is the whole point (FR-012).

Ordered by `weekday`, then `start_time`.

---

## `POST /api/hymnal-history/service-windows/`

- **Auth**: `IsAdminUser`

### Request

```json
{
  "name": "Culto de Sábado",
  "weekday": 7,
  "start_time": "19:30",
  "end_time": "21:00",
  "active": true,
  "takes_rota": false
}
```

`active` and `takes_rota` are optional and both default to `true`.

### Validation

| Rule | Message |
|------|---------|
| `weekday` in 1–7 | names the offending value and the range, with `1 = Sunday` spelled out |
| `end_time` strictly after `start_time` | names both values |
| `name` non-empty, ≤ 100 chars | |

Enforced at the serializer and by database check constraints, so neither the admin site nor a shell
session can create an invalid service.

### Response `201` — the created service.

**Creating a service with `takes_rota: true` puts it into rota generation from the next preview.**
That is the intended behaviour and worth knowing before clicking save.

---

## `GET` / `PATCH` / `DELETE /api/hymnal-history/service-windows/{id}/`

- **Auth**: `IsAdminUser` · **View**: `ServiceWindowDetailAPI`

| Method | Response | Notes |
|--------|----------|-------|
| `GET` | `200` with the service | |
| `PATCH` | `200` with the updated service | Partial; validated against the merged result |
| `DELETE` | `204` — **only if nothing references it** | see below |

`404` with `error_code: "NOT_FOUND"` when the id does not exist.

### ⚠️ `DELETE` is now protected — this is the point of the feature's first task

**Before this feature**, `MonthlySchedule.schedule_type` cascaded. Deleting a service deleted every
rota row that ever referenced it. Once these endpoints point at the shared catalogue, that path
becomes reachable from what looks like a hymnal display setting — 91 rota rows destroyed by one
click, silently, with no undo.

**After**, deleting a service that has rota rows or member configurations returns:

```json
{
  "error_code": "CONFLICT",
  "detail": "Service 'Domingo Liturgia de Adoração' cannot be deleted: 31 rota entries reference it.",
  "service_id": 3,
  "rota_entries": 31
}
```

Status `409`. The message names the service and the count, so the admin knows what they were about
to lose.

**Deactivate instead.** `PATCH {"active": false}` removes a service from future rota generation and
from hymn grouping while keeping every past record intact. That is the intended path for a service
the church stops holding, and the error message should say so.

### Effect on stored data

Editing a service never rewrites history:
- **Rota rows** record what happened; changing a service's time does not retime past rotas.
- **Hymn occurrences** are derived at read time, so they re-interpret on the next read — same as
  feature 006, just sourced from the shared catalogue now.
