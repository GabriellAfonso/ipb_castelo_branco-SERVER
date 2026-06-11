# Gallery — Plan

## Decisions already made

- **No service/repository layer** — views query ORM directly. This violates Clean Architecture (§2) and needs refactoring.
- **PIL** for server-side image validation (`Image.verify()`).
- **Django admin view** for upload (not a DRF endpoint) — admin-only operation, HTML form is sufficient.
- **DRF APIView** for read-only API endpoints (no ViewSets).
- **`select_related("album")`** on photo queries to avoid N+1.
- **No pagination** on photo list endpoints.
- **`IsMemberUser`** permission on all API endpoints.

## Architecture target

Align with Clean Architecture:

```
Views (gallery.py, upload.py)
  -> GalleryService
    -> GalleryRepository (ORM queries)
      -> Album, Photo models
```

- Repository: all ORM access (list photos, filter by album, create photo)
- Service: upload validation logic (size check, image verify), delegates persistence to repository
- Views: HTTP handling only, delegate to service
- Register service + repository in `config/di.py`
- DTOs (Pydantic) for data crossing service boundary
