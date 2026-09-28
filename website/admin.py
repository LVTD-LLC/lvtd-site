from django.contrib import admin

from website.models import BlogPost, StripeWebhookEvent


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "published_at", "updated_at")
    list_filter = ("is_published",)
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "summary", "body")
    ordering = ("-published_at", "-updated_at")

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.slug == "jev-ai-model-benchmark":
            return ("body", "slug", "article_source")
        return super().get_readonly_fields(request, obj)

    def get_prepopulated_fields(self, request, obj=None):
        if obj and obj.slug == "jev-ai-model-benchmark":
            return {}
        return super().get_prepopulated_fields(request, obj)

    @admin.display(description="Article editing")
    def article_source(self, obj):
        return (
            "This illustrated article is repository-owned. Edit "
            "website/templates/website/articles/jev_ai_model_benchmark.html "
            "through a pull request. Body and slug are read-only here; title, "
            "summary, publication date, and visibility remain editable."
        )


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "created_at")
    search_fields = ("event_id",)
    ordering = ("-created_at",)
