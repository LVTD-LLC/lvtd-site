from datetime import UTC, datetime

from django.db import migrations

SLUG = "jev-ai-model-benchmark"
DEFAULTS = {
    "title": "Jev AI benchmark: 29 models, one judge",
    "summary": (
        "We used Jev to judge 29 AI models across four tasks. "
        "Explore 1,624 comparisons, surprising results, costs, "
        "and the limits of the rankings."
    ),
    "body": (
        "This illustrated article is maintained in the repository at "
        "website/templates/website/articles/jev_ai_model_benchmark.html."
    ),
    "published_at": datetime(2026, 9, 28, 16, 30, tzinfo=UTC),
    "is_published": True,
}


def publish(apps, schema_editor):
    posts = apps.get_model("website", "BlogPost").objects.using(
        schema_editor.connection.alias
    )
    posts.get_or_create(slug=SLUG, defaults=DEFAULTS)


def reverse_publish(apps, schema_editor):
    # Preserve any editorial changes made after publication.
    posts = apps.get_model("website", "BlogPost").objects.using(
        schema_editor.connection.alias
    )
    posts.filter(slug=SLUG, **DEFAULTS).delete()


class Migration(migrations.Migration):
    dependencies = [("website", "0003_intro_blog_post")]
    operations = [migrations.RunPython(publish, reverse_publish)]
