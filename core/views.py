from django.shortcuts import render


def index(request):
    """Render the single accessible AVA control page."""
    return render(request, "ava/index.html")
