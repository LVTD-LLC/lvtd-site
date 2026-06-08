from __future__ import annotations

from datetime import UTC, datetime

from django.db import migrations

INTRO_POST_SLUG = "what-lvtd-builds"


INTRO_POST_BODY = "\n\n".join(
    [
        (
            "LVTD is the place where I collect the practical software work I do "
            "for founders, teams, and internet businesses."
        ),
        (
            "The work usually falls into a few buckets: MVP builds, "
            "backend-heavy product development, automations, internal tools, "
            "technical debugging, and small growth systems that need to be "
            "useful quickly. I care about shipping, but I care just as much "
            "about leaving behind a foundation that can survive the next round "
            "of product decisions."
        ),
        (
            "This blog will be a working notebook for that kind of engineering. "
            "Expect notes on choosing boring infrastructure, building useful "
            "automation, debugging production systems, making Django products "
            "easier to operate, and turning rough product ideas into something "
            "real customers can try."
        ),
        (
            "If you are deciding whether LVTD is a fit for your project, start "
            "with the homepage and the Hosted OpenClaw service page. If you want "
            "a more specific answer, email a short note with your context, "
            "goals, timeline, and the constraints that matter."
        ),
    ]
)


def create_intro_blog_post(apps, schema_editor):
    blog_post = apps.get_model("website", "BlogPost")
    blog_post.objects.update_or_create(
        slug=INTRO_POST_SLUG,
        defaults={
            "title": "What LVTD builds",
            "summary": (
                "An introduction to LVTD's product engineering, automation, "
                "technical debugging, and consulting work."
            ),
            "body": INTRO_POST_BODY,
            "published_at": datetime(2026, 6, 8, 12, 0, tzinfo=UTC),
            "is_published": True,
        },
    )


def remove_intro_blog_post(apps, schema_editor):
    blog_post = apps.get_model("website", "BlogPost")
    blog_post.objects.filter(slug=INTRO_POST_SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0002_blogpost"),
    ]

    operations = [
        migrations.RunPython(create_intro_blog_post, remove_intro_blog_post),
    ]
