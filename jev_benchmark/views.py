from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_safe

from .rankings import leaderboard


@require_safe
def index(request):
    return render(request, "jev_benchmark/index.html", leaderboard())


@require_safe
def detail(request, slug):
    context = leaderboard()
    section = next((s for s in context["sections"] if s["question"].slug == slug), None)
    if section is None:
        raise Http404
    return render(request, "jev_benchmark/detail.html", {**context, **section})
