"""
URL หลักของระบบ Radar หุ้น
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from radar.google_auth import google_login, me, logout_api

# ปรับชื่อหน้า Admin เป็นภาษาไทย
admin.site.site_header = "ระบบ Radar หุ้น"
admin.site.site_title = "Radar หุ้น"
admin.site.index_title = "จัดการระบบ"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("radar.urls")),
    path("engine/", include("engine_api.urls")),
    # Auth — Google OAuth + Me + Logout
    path("api/auth/google/",  google_login,  name="google-login"),
    path("api/auth/me/",      me,            name="auth-me"),
    path("api/auth/logout/",  logout_api,    name="auth-logout"),
    path("accounts/", include("allauth.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
