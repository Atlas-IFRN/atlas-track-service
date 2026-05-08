from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def health_check(request):
    return HttpResponse("OK", status=200)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check),
    path('api/tracks/', include('apps.tracks.urls')),
]
