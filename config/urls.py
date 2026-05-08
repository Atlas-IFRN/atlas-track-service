from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Conectando a nossa rota apontando para a pasta apps:
    path('api/tracks/', include('apps.tracks.urls')),
]
