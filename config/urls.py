from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health_check(request):
    return HttpResponse("OK", status=200)


urlpatterns = [
    path('api/track/admin/', admin.site.urls),
    path('health/', health_check),

    path('api/track/', include('apps.tracks.urls')),

    path('api/track/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/track/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
