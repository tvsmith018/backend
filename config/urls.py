"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from config.admin_site import apply_superuser_only_admin_access
from config.graphql_security import build_graphql_view
from config.health import health

apply_superuser_only_admin_access(admin.site)

api_doc_patterns = []
if settings.API_DOCS_ENABLED:
    api_doc_patterns = [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
    ]

urlpatterns = api_doc_patterns + [
    path("health/", health),
    path('admin/', admin.site.urls),
    path(
        "graphql/",
        # GraphQL auth is header-token based (JWT), so CSRF cookie checks are not used.
        # Keep CSRF exemption, but explicitly constrain methods to reduce attack surface.
        csrf_exempt(
            require_http_methods(["POST", "OPTIONS"])(build_graphql_view())
            if settings.IS_PRODUCTION and settings.GRAPHQL_POST_ONLY_IN_PRODUCTION
            else require_http_methods(["GET", "POST", "OPTIONS"])(build_graphql_view())
        ),
    ),
    path('authorized/',include('users.urls')),
    path("profiles/", include("profiles.urls")),
    path('articles/',include('articles.urls')),
    path('payments/', include('payments.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
