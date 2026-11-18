from importlib import import_module

from django.db import migrations
from django.utils import timezone

original = import_module("website.migrations.0003_intro_blog_post")
OLD_SUMMARY = (
    "An introduction to LVTD's product engineering, automation, "
    "technical debugging, and consulting work."
)
SUMMARY = "A short introduction to the software, games, and experiments at LVTD."
BODY = (
    "LVTD is where I keep the things I build. Some start as tools I want to use "
    "myself. ShipRust puts accounts, billing, and deployment into a Rust "
    "starter. TastefulKit gives me somewhere to look when "
    "I need a reference for a design.\n\n"
    "Other projects start with a question. Which model gives a better answer "
    "for the money? The Jev Benchmark keeps the prompts, judgments, and costs "
    "together so you can look for yourself.\n\n"
    "There are browser games here too, from a Russian word puzzle to a "
    "two-player race. The blog is my notebook for what I learn making them."
)


def update_post(apps, editor, old_body, new_body, old_summary, new_summary):
    posts = apps.get_model("website", "BlogPost").objects.using(editor.connection.alias)
    post = posts.filter(slug=original.INTRO_POST_SLUG)
    post.filter(body=old_body).update(body=new_body, updated_at=timezone.now())
    post.filter(summary=old_summary).update(
        summary=new_summary, updated_at=timezone.now()
    )


def forward(apps, editor):
    update_post(apps, editor, original.INTRO_POST_BODY, BODY, OLD_SUMMARY, SUMMARY)


def backward(apps, editor):
    update_post(apps, editor, BODY, original.INTRO_POST_BODY, SUMMARY, OLD_SUMMARY)


class Migration(migrations.Migration):
    dependencies = [("website", "0006_jev_reader_first")]
    operations = [migrations.RunPython(forward, backward)]
