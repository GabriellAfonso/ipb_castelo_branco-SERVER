from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

from apps.gallery.models.gallery import Album, Photo


# TODO: gambiarra temporaria — substituir por uma APIView dedicada de upload
def _build_upload_html(albums):
    options = "".join(
        f'<option value="{album.pk}">{album.name}</option>'
        for album in albums
    )
    return f"""
    <html>
    <body>
        <form method="post" enctype="multipart/form-data">
            <select name="album">{options}</select>
            <input type="file" name="images" multiple accept="image/*">
            <button type="submit">Upload</button>
        </form>
    </body>
    </html>
    """


@require_http_methods(["GET", "POST"])
def upload_photos(request):
    albums = Album.objects.all()

    if request.method == "POST":
        album_id = request.POST.get("album")
        files = request.FILES.getlist("images")

        if album_id and files:
            album = Album.objects.get(pk=album_id)

            for f in files:
                Photo.objects.create(
                    album=album,
                    image=f,
                    name=f.name
                )

            return redirect("upload_photos")

    return HttpResponse(_build_upload_html(albums))
