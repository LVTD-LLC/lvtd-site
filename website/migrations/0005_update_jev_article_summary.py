from datetime import UTC, datetime

from django.db import migrations

SLUG = "jev-ai-model-benchmark"
OLD = (
    "We used Jev to judge 29 AI models across four tasks. "
    "Explore 1,624 comparisons, surprising results, costs, "
    "and the limits of the rankings."
)
NEW = (
    "Six tasks changed our Jev AI benchmark winner. Explore 29 models, "
    "2,436 comparisons, updated costs, and what the results do and do not prove."
)


def update_summary(apps, schema_editor):
    posts = apps.get_model("website", "BlogPost").objects.using(
        schema_editor.connection.alias
    )
    posts.filter(slug=SLUG, summary=OLD).update(
        summary=NEW, updated_at=datetime(2026, 9, 28, 19, 0, tzinfo=UTC)
    )


def reverse_summary(apps, schema_editor):
    posts = apps.get_model("website", "BlogPost").objects.using(
        schema_editor.connection.alias
    )
    posts.filter(slug=SLUG, summary=NEW).update(summary=OLD)


class Migration(migrations.Migration):
    dependencies = [("website", "0004_jev_benchmark_article")]
    operations = [migrations.RunPython(update_summary, reverse_summary)]
