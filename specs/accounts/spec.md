# Accounts Domain Spec

Manages user identity, authentication, and profile. Single entry point for who the user is and how they prove it.

---

## Data Models

### User
- `id`: UUID (PK, auto-generated)
- `username`: string, max 150, unique, stored lowercase/trimmed
- `email`: string, unique (used by Google OAuth)
- `first_name`: string, max 30
- `last_name`: string, max 150
- `password`: hashed (unusable for Google-only users)
- Inherits from Django `AbstractUser`

### Profile
- `user`: OneToOne -> User (cascade delete)
- `name`: string, max 100, blank allowed (auto-filled from first_name + last_name on creation)
- `photo`: ImageField, nullable (stored at `profiles/{username}/profile_picture.{ext}`)
- `active`: bool, default true
- `is_member`: bool, default false
- `is_admin`: bool, default false

### Signals (current behavior)
- **post_save User (created)**: auto-creates Profile with `name = "{first_name} {last_name}".strip().title()`
- **post_save User**: saves related profile on every user save
- **pre_save Profile**: deletes old photo file from disk when photo field changes
- **post_delete Profile**: deletes photo file from disk

---

## DTOs (Pydantic)

| DTO | Fields | Used by |
|-----|--------|---------|
| `RegisterDTO` | username, password, first_name, last_name | Register flow |
| `LoginDTO` | username, password | Login flow |
| `TokenDTO` | access, refresh (optional) | All auth responses |

All inherit from `StrictBaseModel`. Username normalized (strip + lowercase) via field_validator.

---

## Endpoints

All under `/ipbcb/accounts/`.

### POST `api/auth/register/`
- **Public**, throttled (scope: `login`)
- Input: username, first_name, last_name, password, password_confirm
- Validation: username uniqueness, passwords match, min 6 chars
- Returns: `TokenDTO` (201)
- Flow: Serializer validates -> DTO -> UserRepository.create() -> JWT tokens

### POST `api/auth/login/`
- **Public**, throttled (scope: `login`)
- Input: username, password
- Returns: `TokenDTO` (200) or 401
- Flow: DTO validates -> `django.contrib.auth.authenticate()` -> JWT tokens

### POST `api/auth/google/`
- **Public**, throttled (scope: `login`)
- Input: `id_token` (Google OAuth2 ID token)
- Validates token against `GOOGLE_CLIENT_ID`
- Requires verified email
- Creates user if not exists (username from email prefix, collision-safe with counter suffix)
- Sets unusable password for Google-created users
- Downloads Google profile photo (400px, square crop) on first login if profile has no photo
- Returns: `TokenDTO` (200) or 400/401

### POST `api/auth/refresh/`
- **Public** (SimpleJWT built-in `TokenRefreshView`)
- Input: refresh token
- Returns: new access token

### GET `api/me/profile/`
- **Authenticated**
- Returns: name, active, is_admin, is_member, photo_url
- Supports ETag (`If-None-Match` -> 304)
- Auto-creates Profile if missing (get_or_create)

### PATCH `api/me/profile/`
- **Authenticated**
- Updatable: `name` only (active, is_admin, is_member, photo_url are read-only)
- Returns: updated profile (200)

### POST `api/me/profile/photo/`
- **Authenticated**
- Input: multipart photo file
- Deletes old photo before saving new one
- Returns: detail message + photo_url (200)

### DELETE `api/me/profile/photo/`
- **Authenticated**
- Removes photo from profile and disk
- Returns: 204

---

## Business Rules

1. Username is always stored lowercase and trimmed
2. Username must be unique (checked at serializer level)
3. No password complexity requirements — any password >= 6 chars accepted
4. Google users get unusable password — cannot login via username/password
5. Google photo only downloaded on first login when profile has no photo yet
6. Google username collision resolved by appending incrementing counter (e.g., `john`, `john1`, `john2`)
7. Profile auto-created on user creation (via signal) and on profile access (via get_or_create)
8. Old profile photos deleted from filesystem when replaced or profile deleted
9. All auth endpoints share `login` throttle scope

---

## Errors

| Situation | Status | Message |
|-----------|--------|---------|
| Missing id_token | 400 | "id_token e obrigatorio." |
| Invalid Google token | 401 | "Token do Google invalido." |
| Unverified Google email | 400 | "Conta Google sem email verificado." |
| Google user creation failure | 500 | "Erro ao criar usuario." |
| Invalid credentials (login) | 401 | "Nome de usuario ou senha invalidos." |
| Username taken (register) | 400 | Validation error on username field |
| Passwords don't match | 400 | Validation error on password_confirm field |
| Profile not found (photo delete) | 404 | "Perfil nao encontrado." |

---

## Architecture (current state)

```
Views (auth.py, profile.py)
  |
  +---> Serializers (validation + DTO creation)
  |
  +---> UserRepository (only used by RegisterAPI)
  |
  +---> Models directly (GoogleLoginAPI, ProfileViews bypass repository)
```

### Known violations against constitution.md

1. **No service layer** — Views contain business logic directly
2. **Views access ORM** — GoogleLoginAPI uses `User.objects` directly; profile views use `Profile.objects`
3. **DI partial** — Only RegisterAPI injects UserRepository; GoogleLoginAPI bypasses it
4. **No Google auth DTO** — Google token data extracted as raw dict values, no Pydantic validation
5. **Repository incomplete** — Missing `get_by_email()`, `username_exists()`, `get_or_create_profile()`
6. **Broad exception catch** — `except Exception:` in GoogleLoginAPI hides root cause
7. **Serializer touches ORM** — `RegisterSerializer.validate_username()` queries `User.objects` directly

### Target architecture

```
Views (thin HTTP layer)
  |
  +---> Serializers (I/O validation only, no ORM)
  |
  +---> Services (business logic, orchestration)
  |       +---> RegisterService
  |       +---> LoginService
  |       +---> GoogleAuthService
  |       +---> ProfileService
  |
  +---> Repositories (ORM access)
          +---> UserRepository (complete: create, get_by_email, username_exists, etc.)
          +---> ProfileRepository (get_or_create, update_photo, delete_photo)
```

All services injected via `config/di.py`. Domain errors as exceptions from `core/domain/exceptions.py`.
