# Bible Domain

Read-only domain that serves Bible text data. No authentication required — fully public.

## Overview

Provides Bible versions (e.g., ARA, NAA) as structured JSON loaded from static files at startup. The Android app uses this to display Bible text offline-capable after first fetch.

## Data Model

No database models. Data lives in static JSON files under `features/bible/data/`.

### Bible JSON Structure

Each file is named `{VERSION}.json` (e.g., `ARA.json`) and contains a list of books:

```json
[
  {
    "abbrev": "Gn",
    "name": "Gênesis",
    "chapters": [
      ["Verso 1", "Verso 2", "..."],
      ["Verso 1 do cap 2", "..."]
    ]
  }
]
```

| Field      | Type              | Description                                      |
|------------|-------------------|--------------------------------------------------|
| `abbrev`   | `str`             | Standard abbreviation of the book                |
| `name`     | `str`             | Full name of the book (pt-BR)                    |
| `chapters` | `list[list[Verse]]` | List of chapters, each chapter is a list of verses. `Verse = str \| list[str]` — most verses are plain strings, but some entries (e.g., NAA) contain nested lists for multi-paragraph verses. |

### Adding a new version

Drop a new `{VERSION}.json` file in `features/bible/data/`. It is loaded automatically at startup.

## Endpoints

### `GET /api/bible/`

Lists available Bible versions.

- **Auth:** none (`AllowAny`)
- **Response `200`:**

```json
{
  "versions": ["ARA", "NAA"]
}
```

Versions are returned sorted alphabetically.

### `GET /api/bible/{name}/`

Returns full Bible data for a specific version.

- **Auth:** none (`AllowAny`)
- **Path params:** `name` — version identifier (case-sensitive, must match filename stem)
- **Response `200`:** the Bible JSON structure (list of books)
- **Response `404`:**

```json
{
  "detail": "Version not found."
}
```

## Business Rules

1. Bible data is **read-only** — no create, update, or delete operations.
2. All versions are loaded **once** (lazily via DI Singleton) from JSON files. No runtime reloading.
3. Version lookup is **case-sensitive** — `ARA` and `ara` are different keys.
4. Endpoints are **public** — no authentication required.

## Errors

| Scenario               | Error                          |
|------------------------|--------------------------------|
| Unknown version name   | `BibleVersionNotFound` (→ 404) |
