from decimal import Decimal

import pytest
from django.core.management import call_command

from jev_benchmark.models import Answer, BenchmarkModel, Comparison, Question

pytestmark = pytest.mark.django_db


def cohort():
    q = Question.objects.create(
        title="Evidence",
        slug="evidence",
        category="writing",
        prompt="Use source [A].",
        rubric="Faithful.",
    )
    models = [
        BenchmarkModel.objects.create(
            name=f"Model {i}", provider="Lab", openrouter_id=f"lab/{i}"
        )
        for i in range(6)
    ]
    answers = [
        Answer.objects.create(
            model=m,
            question=q,
            status="complete",
            text=f"Answer {i}",
            response={
                "usage": {"cost": str(Decimal(i) / 1000)},
                "secret_internal": "DO_NOT_EXPORT",
            },
            request={"max_tokens": 8192, "Authorization": "DO_NOT_EXPORT"},
        )
        for i, m in enumerate(models)
    ]
    for i, a in enumerate(answers):
        for b in answers[i + 1 :]:
            Comparison.objects.create(
                question=q,
                left=a,
                right=b,
                status="complete",
                choice="A",
                confidence=0.8,
                probabilities={"A": 0.8, "B": 0.2},
            )
    return q, models, answers


def test_value_score_is_bounded_monotonic_and_missing_is_not_free():
    from jev_benchmark.value import value_score

    assert value_score(1500, Decimal(".01")) == pytest.approx(50)
    assert value_score(1500, Decimal(0)) == pytest.approx(65)
    assert value_score(1600, Decimal(".01")) > value_score(1500, Decimal(".01"))
    assert value_score(1500, Decimal(".001")) > value_score(1500, Decimal(".01"))
    assert value_score(None, Decimal(0)) is None
    assert value_score(1500, None) is None
    assert 0 <= value_score(500, Decimal(100)) <= 100


def test_tables_expand_and_export_preserves_evidence_without_internal_payload(client):
    cohort()
    page = client.get("/jev-benchmark").content.decode()
    assert "Answers / judging coverage" not in page
    assert "bench-eyebrow" not in page
    assert "Show all 6 models" in page
    assert "data-extra-row" in page
    result = client.get("/jev-benchmark/data.json")
    assert result.status_code == 200
    data = result.json()
    assert data["schema_version"] == "jev-benchmark/v1"
    assert len(data["answers"]) == 6 and len(data["judgments"]) == 15
    assert data["answers"][0]["text"] == "Answer 0"
    assert data["answers"][0]["cost_usd"] == "0"
    assert data["questions"][0]["prompt"] == "Use source [A]."
    assert "DO_NOT_EXPORT" not in result.content.decode()
    assert len(data["dataset_sha256"]) == 64
    again = client.get("/jev-benchmark/data.json")
    assert again.json()["dataset_sha256"] == data["dataset_sha256"]
    assert client.get("/jev-benchmark/methodology.md").status_code == 200


def test_new_questions_idempotent_and_do_not_change_existing_answers():
    q, _, answers = cohort()
    before = list(Answer.objects.values())
    call_command("add_jev_questions")
    call_command("add_jev_questions")
    assert Question.objects.count() == 3
    assert list(Answer.objects.values()) == before
    assert set(
        Question.objects.exclude(pk=q.pk).values_list("category", flat=True)
    ) == {"analysis", "synthesis"}


def test_value_requires_complete_priced_scope():
    from jev_benchmark.rankings import leaderboard

    _, _, answers = cohort()
    row = leaderboard()["overall"][0]
    assert row["value_score"] is not None
    Answer.objects.filter(pk=answers[0].pk).update(response={})
    row = next(
        r for r in leaderboard()["overall"] if r["model"].pk == answers[0].model_id
    )
    assert row["value_score"] is None


def test_weighted_cost_matches_question_weights_and_incomplete_is_unscored():
    from jev_benchmark.rankings import leaderboard
    from jev_benchmark.value import value_score

    first, models, _ = cohort()
    second = Question.objects.create(
        title="Second",
        slug="second",
        category="math",
        prompt="Analyze.",
        rubric="Correct.",
        weight=3,
    )
    answers = [
        Answer.objects.create(
            model=m,
            question=second,
            status="complete",
            text="Answer",
            response={"usage": {"cost": "0.012"}},
        )
        for m in models
    ]
    for i, a in enumerate(answers):
        for b in answers[i + 1 :]:
            Comparison.objects.create(
                question=second,
                left=a,
                right=b,
                status="complete",
                choice="A",
                confidence=0.8,
            )
    row = next(r for r in leaderboard()["overall"] if r["model"] == models[0])
    assert row["mean_cost_usd"] == Decimal(".009")
    assert row["value_score"] == pytest.approx(
        value_score(row["rating"], Decimal(".009"))
    )
    Comparison.objects.filter(question=second, left=answers[0]).first().delete()
    row = next(r for r in leaderboard()["overall"] if r["model"] == models[0])
    assert row["value_score"] is None


def test_export_checksum_can_be_recomputed(client):
    import hashlib
    import json

    cohort()
    data = client.get("/jev-benchmark/data.json").json()
    checksum = data.pop("dataset_sha256")
    data.pop("exported_at")
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(canonical.encode()).hexdigest() == checksum
