# Contract: Reporting Endpoints

Both endpoints read the same derived **occurrence** — a hymn sung once by the congregation, not once
per person. Collapse key: hymn + service window, falling back to hymn + calendar day outside every
active window. See `data-model.md` for the full rule.

A window's match extends past its `end_time` by `window_grace_minutes` (default 30), because
services run long. The start is not extended. Changing that setting re-interprets stored history on
the next read without altering a single event.

Both are `IsAdminUser` (`core/http/permissions.py` — authenticated with `profile.is_admin`), the
same permission guarding Sunday repertoire registration.

---

## `GET /api/hymnal-history/occurrences/`

Dashboard by period. One endpoint covers week, month, year and any custom range.

- **View**: `HymnalHistoryOccurrencesAPI` · **URL name**: `hymnal_history_occurrences`

### Query parameters

| Param | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `from` | date `YYYY-MM-DD` | no | `to` − 30 days | Inclusive, church local time |
| `to` | date `YYYY-MM-DD` | no | today | Inclusive, church local time |
| `group_by` | enum | no | `service` | `service` \| `day` \| `week` \| `month` |

Dates are inclusive days in `America/Sao_Paulo`, converted internally to the half-open aware
interval `[from 00:00, to+1d 00:00)` so the last day's evening service is included.

### Response `200`

```json
{
  "from": "2026-08-01",
  "to": "2026-08-31",
  "group_by": "service",
  "occurrences": [
    {
      "hymn_number": "50",
      "hymn_title": "Grandioso És Tu",
      "occurred_on": "2026-08-09",
      "service_window_id": 3,
      "service_window_name": "Culto de Domingo à Noite",
      "bucket": "2026-08-09:3",
      "device_count": 27
    },
    {
      "hymn_number": "120",
      "hymn_title": "Saudosa Lembrança",
      "occurred_on": "2026-08-12",
      "service_window_id": null,
      "service_window_name": null,
      "bucket": "2026-08-12:none",
      "device_count": 2
    }
  ]
}
```

`service_window_id: null` means the views fell outside every active window and collapsed by calendar
day instead — the second entry above is a Wednesday afternoon, not a service.

**Ordering**: `occurred_on` ascending, then `service_window.start_time` (nulls last), then hymn
number. Stable, so the chart does not reshuffle between identical requests.

**Bucket format** by `group_by`: `service` → `"{date}:{window_id}"` or `"{date}:none"`;
`day` → `2026-08-09`; `week` → `2026-W32` (ISO); `month` → `2026-08`.

`group_by` changes only the `bucket` label. It never changes how occurrences collapse, so the same
range always yields the same number of occurrences regardless of grouping.

**No pagination** — the range is bounded at 366 days and the only client renders a list or a chart
(spec Assumptions). Consistent with the other list endpoints in this domain.

### Errors

| Status | `error_code` | When |
|--------|--------------|------|
| `400` | `VALIDATION_ERROR` | `from` after `to`; span over 366 days; unparseable date; `group_by` not in the enum |
| `401` | `NOT_AUTHENTICATED` | No credentials |
| `403` | `PERMISSION_DENIED` | Authenticated but not an admin |

---

## `GET /api/hymnal-history/top-hymns/`

Ranking / chart data — X is the hymn number, Y is how many times it was sung.

- **View**: `HymnalHistoryTopHymnsAPI` · **URL name**: `hymnal_history_top_hymns`

### Query parameters

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `from` | date `YYYY-MM-DD` | no | all time |
| `to` | date `YYYY-MM-DD` | no | all time |

Omitting both covers all recorded history. Supplying one without the other bounds only that side.

### Response `200`

```json
{
  "from": null,
  "to": null,
  "hymns": [
    { "hymn_number": "50",  "hymn_title": "Grandioso És Tu",   "occurrence_count": 42 },
    { "hymn_number": "12",  "hymn_title": "Firme nas Promessas", "occurrence_count": 31 },
    { "hymn_number": "120", "hymn_title": "Saudosa Lembrança",  "occurrence_count": 3 }
  ]
}
```

- Counts **occurrences**, not raw events: five devices contributing to one occurrence count as 1.
- Only hymns with at least one occurrence in the range appear — the client fills the gaps.
- Ordered by `occurrence_count` descending, then hymn number ascending as a stable tie-break.

### Errors

Same as the occurrences endpoint, minus `group_by`. The all-time default means the 366-day cap does
**not** apply here; the response is one row per distinct hymn, so it is bounded by the size of the
hymnal regardless of how much history exists.
