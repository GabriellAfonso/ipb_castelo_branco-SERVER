# Gallery — Tasks

## Architecture alignment

- [x] Create `GalleryRepository` — extract all ORM queries from views
- [x] Create `GalleryService` — extract upload validation logic from `upload.py`
- [x] Create Pydantic DTO (`UploadResult`) for upload operation
- [x] Register repository and service in `config/di.py`
- [x] Update views to call service instead of ORM directly
- [x] Update tests for new layered structure

## Bug fixes

- [x] Escape `album.name` in `_build_upload_html` — potential XSS (admin-only, low risk)
