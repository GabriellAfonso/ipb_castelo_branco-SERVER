from dependency_injector.wiring import Provide, inject
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.utils.html import escape

from config.di import Container
from core.domain.exceptions import NotFoundError
from features.gallery.models.gallery import Album
from features.gallery.services.gallery_service import GalleryService


def _build_upload_html(
    request: HttpRequest,
    albums: QuerySet[Album],
    errors: list[str] | None = None,
) -> str:
    csrf_token = get_token(request)
    options = "".join(
        f'<option value="{album.pk}">{escape(album.name)}</option>' for album in albums
    )
    errors_html = "".join(f'<p style="color:red">{escape(e)}</p>' for e in (errors or []))
    return f"""
    <html>
    <body>
        {errors_html}
        <form method="post" enctype="multipart/form-data">
            <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
            <select name="album">{options}</select>
            <input type="file" name="images" multiple accept="image/*">
            <button type="submit">Upload</button>
        </form>
    </body>
    </html>
    """


@inject
def upload_photos(
    request: HttpRequest,
    gallery_service: GalleryService = Provide[Container.gallery_service],
) -> HttpResponse:
    albums = gallery_service.list_all_albums()

    if request.method == "POST":
        album_id = request.POST.get("album")
        files = request.FILES.getlist("images")

        if not album_id or not files:
            return HttpResponse(
                _build_upload_html(request, albums, ["Selecione um álbum e ao menos uma imagem."])
            )

        try:
            result = gallery_service.upload_photos(int(album_id), files)
        except NotFoundError:
            return HttpResponse(_build_upload_html(request, albums, ["Álbum não encontrado."]))

        if result.has_errors:
            return HttpResponse(_build_upload_html(request, albums, result.errors))

        return redirect("admin:gallery_album_changelist")

    return HttpResponse(_build_upload_html(request, albums))
