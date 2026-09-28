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


@require_safe
def dataset(request):
    from django.http import JsonResponse

    from .exports import public_dataset

    response = JsonResponse(public_dataset(), json_dumps_params={"indent": 2})
    response["Content-Disposition"] = 'attachment; filename="jev-benchmark-v1.json"'
    response["Cache-Control"] = "no-cache"
    return response


@require_safe
def methodology(request):
    from django.http import HttpResponse

    from .exports import METHODOLOGY

    return HttpResponse(METHODOLOGY, content_type="text/markdown; charset=utf-8")
