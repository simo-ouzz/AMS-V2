"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib import admin
from django.urls import path, include,re_path
from django.views.i18n import set_language
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect, HttpResponseNotFound, JsonResponse
from django.views.defaults import page_not_found, server_error, bad_request
import logging

logger = logging.getLogger(__name__)

def health_check(request):
    """Health check endpoint for Docker/Kubernetes"""
    return JsonResponse({"status": "OK"})

def custom_404(request, exception):
    logger.warning(f"404 error: {request.path}")
    return HttpResponseNotFound(f"""
        <html>
        <head><title>404 - Page Not Found</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>404 - Page Not Found</h1>
            <p>The page you requested could not be found.</p>
            <a href="/admin/">Go to Admin</a>
        </body>
        </html>
    """)

def custom_500(request):
    logger.error(f"500 error: {request.path}")
    return HttpResponseNotFound(f"""
        <html>
        <head><title>500 - Server Error</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>500 - Server Error</h1>
            <p>Something went wrong on our end.</p>
            <a href="/admin/">Go to Admin</a>
        </body>
        </html>
    """)

handler404 = custom_404
handler500 = custom_500



urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('masterdata.urls')),  # APIs sous 'api/'
    path('set_language/', set_language, name='set_language'),
    path('health/', health_check, name='health'),  # Docker health check
    path('', lambda request: HttpResponseRedirect('/admin/')), 
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
