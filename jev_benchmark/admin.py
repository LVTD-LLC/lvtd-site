from django.contrib import admin
from django.utils import timezone

from .models import (
    Answer,
    BenchmarkModel,
    BudgetState,
    Comparison,
    Question,
    WorkAttempt,
)


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
    list_filter = ("status", "error_kind", "question")
    actions = ["retry_failed"]

    @admin.action(description="Retry selected failed work (may incur API charges)")
    def retry_failed(self, request, queryset):
        count = queryset.filter(status="failed").update(
            error_kind="transient", retry_count=0, next_attempt_at=timezone.now()
        )
        self.message_user(
            request, f"{count} failed jobs queued; completed results untouched."
        )

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


@admin.register(WorkAttempt)
class AttemptAdmin(ResultAdmin):
    list_filter = ("status", "source", "error_kind")
    list_display = (
        "id",
        "answer",
        "comparison",
        "number",
        "status",
        "cost_usd",
        "source",
        "started_at",
    )
    actions = None


@admin.register(BudgetState)
class BudgetAdmin(ResultAdmin):
    list_filter = ()
    list_display = ("checked_at", "openrouter_usage", "available_credit", "alert")
    actions = None
