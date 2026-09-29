from datetime import UTC, datetime

from django.db import migrations

SLUG = "jev-ai-model-benchmark"
OLD_TITLE = "Jev AI benchmark: 29 models, one judge"
NEW_TITLE = "Jev benchmark: the best AI models by task and cost"
OLD_SUMMARY = (
    "Six tasks changed our Jev AI benchmark winner. Explore 29 models, "
    "2,436 comparisons, updated costs, and what the results do and do not prove."
)
NEW_SUMMARY = (
    "MiMo Flash leads our six-task benchmark on both Elo and value. "
    "See which models win for writing, coding, math, advice, analysis, and synthesis."
)


def rewrite_metadata(apps, schema_editor):
    posts = apps.get_model("website", "BlogPost").objects.using(
        schema_editor.connection.alias
    )
    # Preserve metadata independently edited since the previous publication.
    posts.filter(slug=SLUG, title=OLD_TITLE).update(title=NEW_TITLE)
    posts.filter(slug=SLUG, summary=OLD_SUMMARY).update(summary=NEW_SUMMARY)
    posts.filter(slug=SLUG).update(updated_at=datetime(2026, 9, 29, 20, 5, tzinfo=UTC))


def reverse_metadata(apps, schema_editor):
    posts = apps.get_model("website", "BlogPost").objects.using(
        schema_editor.connection.alias
    )
    posts.filter(slug=SLUG, title=NEW_TITLE).update(title=OLD_TITLE)
    posts.filter(slug=SLUG, summary=NEW_SUMMARY).update(summary=OLD_SUMMARY)


class Migration(migrations.Migration):
    dependencies = [("website", "0005_update_jev_article_summary")]
    operations = [migrations.RunPython(rewrite_metadata, reverse_metadata)]
