from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "HEAD", "OPTIONS"])
def health(_request):
    """Liveness probe — no database access."""
    return JsonResponse({"status": "ok"})
