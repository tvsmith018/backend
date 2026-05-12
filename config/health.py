from django.http import JsonResponse


def health(_request):
    """Liveness probe — no database access."""
    return JsonResponse({"status": "ok"})
