# Songs Domain Spec

## Purpose

Manages worship songs, play history, hymnal, chord charts, and lyrics for the church app. Provides song suggestions based on play history and supports registering which songs were played each Sunday.

---

## Data Models

### Category

| Field | Type        | Constraints   |
|-------|-------------|---------------|
| name  | CharField   | max=100, unique |

### Song

| Field        | Type         | Constraints                  |
|--------------|--------------|------------------------------|
| title        | CharField    | max=100                      |
| artist       | CharField    | max=100                      |
| category     | FK(Category) | nullable, SET_NULL           |
| youtube_link | URLField     | max=200, blank, default=""   |

### Played

| Field    | Type       | Constraints                      |
|----------|------------|----------------------------------|
| song     | FK(Song)   | nullable, blank, PROTECT         |
| tone     | CharField  | max=3                            |
| position | IntegerField |                                |
| date     | DateField  |                                  |

### Hymn

| Field  | Type       | Constraints         |
|--------|------------|---------------------|
| number | CharField  | max=10, unique (accepts alphanumeric like "110-A") |
| title  | CharField  | max=200             |
| lyrics | JSONField  |                     |

### ChordChart

| Field      | Type         | Constraints                        |
|------------|--------------|-------------------------------------|
| song       | FK(Song)     | CASCADE                            |
| content    | TextField    |                                    |
| tone       | CharField    | max=3, blank                       |
| instrument | CharField    | max=50, blank                      |
| created_at | DateTimeField| auto_now_add                       |
| updated_at | DateTimeField| auto_now                           |

**unique_together**: (song, tone, instrument)

### Lyrics

| Field      | Type           | Constraints  |
|------------|----------------|--------------|
| song       | OneToOne(Song) | CASCADE      |
| content    | TextField      |              |
| created_at | DateTimeField  | auto_now_add |
| updated_at | DateTimeField  | auto_now     |

---

## Endpoints

All endpoints are prefixed with the base path (`/ipbcb/`).

### GET /api/songs/

List all songs with category name.

- **Auth**: AllowAny
- **Response**: `200` with ETag support (304 if unchanged)
- **Response body**: array of `{ id, title, artist, category }`
- **Ordering**: title, artist

### GET /api/songs-by-sunday/

List all plays grouped by date.

- **Auth**: AllowAny
- **Response**: `200` with ETag support
- **Response body**: array of `{ date, songs: [{ song_id, position, song, artist, tone }] }`
- **Ordering**: date desc, position asc
- **Date format**: `dd/mm/yyyy`

### GET /api/top-songs/

Most played songs ranked by play count.

- **Auth**: AllowAny
- **Response**: `200` with ETag support
- **Response body**: array of `{ song_id, song__title, play_count }`

### GET /api/top-tones/

Most used tones ranked by count.

- **Auth**: AllowAny
- **Response**: `200` with ETag support
- **Response body**: array of `{ tone, tone_count }`

### GET /api/suggested-songs/

Suggest songs for positions 1-4. Excludes songs played in the last 90 days.

- **Auth**: AllowAny
- **Query params**:
  - `fixed` (optional): pin specific positions. Format: `"1:12,3:45"` (position:played_id)
- **Response**: `200`
- **Response body**: array of serialized Played objects with overridden position

**Business rules**:
- Only suggests songs not played in last 90 days
- Matches songs to their historical position
- No duplicate songs across positions
- Fixed positions are respected (pinned by Played id)
- Positions limited to 1-4

### GET /api/hymnal/

List all hymns ordered by number (numeric sort, with alphanumeric suffix support).

- **Auth**: AllowAny
- **Response**: `200` with ETag support
- **Response body**: array of `{ number, title, lyrics }`
- **Note**: Uses REGEXP_REPLACE (PostgreSQL only)

### POST /api/played/register/

Register songs played on a given Sunday.

- **Auth**: IsAdminUser (authenticated + admin profile)
- **Request body**:
  ```json
  {
    "date": "2026-02-07",
    "plays": [
      { "song_id": 12, "position": 1, "tone": "G" }
    ]
  }
  ```
- **Validation**:
  - `date` required, format YYYY-MM-DD
  - `plays` required, non-empty list
  - Each play: `song_id` and `position` required integers
  - Position range: 1-10 (allows extra songs for special occasions)
  - All referenced songs must exist
- **Response**: `201 { "created": N }` on success
- **Errors**: `400 { "detail": "..." }` with descriptive messages

### GET /api/chord-charts/

List all chord charts ordered alphabetically by song title.

- **Auth**: AllowAny
- **Response**: `200`
- **Response body**: array of `{ id, song_id, content, tone, instrument, updated_at }`
- **Ordering**: song title (ascending)

### GET /api/lyrics/

List all lyrics ordered alphabetically by song title.

- **Auth**: AllowAny
- **Response**: `200`
- **Response body**: array of `{ id, song_id, content, updated_at }`
- **Ordering**: song title (ascending)

---

## Architecture

Follows clean architecture (Views -> Services -> Repositories -> Models):

- **Repository**: `DjangoSongRepository` (songs, played, chord charts, lyrics), `DjangoHymnalRepository` (hymns)
- **Services**: `SongService` (queries + suggestions), `RegisterPlaysService` (play registration), `HymnalService` (hymnal listing)
- **DI**: All services/repositories registered in `config/di.py`, injected via `@inject` + `Provide[Container.xxx]`

---

## Design Decisions

- **Position 1-4 vs 1-10**: Normal service has 4 songs (positions 1-4). `SuggestedSongsAPI` only suggests for 1-4. `RegisterSundayPlaysAPI` accepts up to 10 for special occasions. This is intentional.
- **AllowAny on most endpoints**: Internal church app, no sensitive data. Only registration of plays requires admin auth.
- **ETag caching**: Read-only list endpoints use SHA-256 ETag for conditional GET (304 Not Modified).
- **Random suggestion**: `random.choice` for song selection — simple and adequate for the use case.
