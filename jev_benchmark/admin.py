from django.contrib import admin

from .models import Answer, BenchmarkModel, Comparison, Question


@admin.register(BenchmarkModel)
class BenchmarkModelAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "openrouter_id", "active")
    list_filter = ("active", "provider")
    search_fields = ("name", "openrouter_id")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "weight", "judge_model", "active")
    list_filter = ("active", "category")
    prepopulated_fields = {"slug": ("title",)}


class ResultAdmin(admin.ModelAdmin):
    list_filter = ("status", "question")

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Answer)
class AnswerAdmin(ResultAdmin):
    list_display = ("model", "question", "status", "attempts", "completed_at")


@admin.register(Comparison)
class ComparisonAdmin(ResultAdmin):
    list_display = (
        "question",
        "left",
        "right",
        "status",
        "choice",
        "confidence",
        "completed_at",
    )
