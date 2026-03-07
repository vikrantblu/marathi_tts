import os
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from tts.views import tts_views

# Admin URL slug — set DJANGO_ADMIN_URL in your environment to obscure it in production
ADMIN_URL = os.getenv('DJANGO_ADMIN_URL', 'admin/')

class CustomLogoutView(auth_views.LogoutView):
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),
    path('marathi_tts/tts/', include('tts.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', CustomLogoutView.as_view(), name='logout'),
    path('', tts_views.entry_page, name='entry_page'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)