from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from jev_benchmark.models import Answer, BenchmarkModel, Question
from jev_benchmark.rankings import leaderboard

pytestmark = pytest.mark.django_db


def sample():
    q = Question.objects.create(
        title="Test", slug="test", category="coding", prompt="Solve.", rubric="Correct."
    )
    a = BenchmarkModel.objects.create(name="A", provider="Lab", openrouter_id="lab/a")
    b = BenchmarkModel.objects.create(name="B", provider="Lab", openrouter_id="lab/b")
    return q, a, b


def test_answers_and_judging_coverage_are_independent(client):
    q, a, b = sample()
    Answer.objects.create(
        model=a,
        question=q,
        status="complete",
        text="Saved",
        response={"usage": {"cost": 0.00125}},
    )
    row = next(x for x in leaderboard()["overall"] if x["model"] == a)
    assert row["answers_count"] == 1
    assert row["questions_complete"] == 0
    assert row["cost_usd"] == Decimal("0.00125")
    page = client.get("/jev-benchmark").content.decode()
    assert "Answers / judging coverage" not in page
    assert "$0.001250" in page
    assert "Unknown" in page


def test_cost_zero_unknown_and_malformed_are_not_conflated():
    from jev_benchmark.costs import reported_cost

    assert reported_cost({"usage": {"cost": 0}}) == Decimal(0)
    for value in (None, True, -1, "NaN", "Infinity", {}, "n/a"):
        assert reported_cost({"usage": {"cost": value}}) is None
    assert reported_cost({}) is None


def test_blocked_model_does_not_stop_other_models():
    from jev_benchmark.clients import ProviderError
    from jev_benchmark.queue import run_queue

    q, a, b = sample()

    def generate(model, question, **kw):
        if model == a:
            raise ProviderError("Privacy blocked", kind="blocked")
        return {
            "text": "ok",
            "response": {"usage": {"cost": 0.002}},
            "request": {},
            "duration_ms": 1,
        }

    with (
        patch("jev_benchmark.queue.generate", side_effect=generate),
        patch("jev_benchmark.queue.CreditBudget", return_value=None),
    ):
        run_queue(workers=2)
    assert Answer.objects.get(model=b).status == "complete"
    assert Answer.objects.get(model=a).error_kind == "blocked"


def test_transient_retry_is_durable_and_bounded():
    from jev_benchmark.clients import ProviderError
    from jev_benchmark.models import WorkAttempt
    from jev_benchmark.queue import run_queue

    q, a, b = sample()
    b.active = False
    b.save()
    with (
        patch(
            "jev_benchmark.queue.generate",
            side_effect=ProviderError("Capacity", kind="transient", retry_after=60),
        ) as call,
        patch("jev_benchmark.queue.CreditBudget", return_value=None),
    ):
        run_queue()
        run_queue()
        assert call.call_count == 1
        for _ in range(3):
            Answer.objects.update(next_attempt_at=timezone.now())
            run_queue()
        assert call.call_count == 3
    assert WorkAttempt.objects.count() == 3
    assert Answer.objects.get(model=a).error_kind == "exhausted"


def test_judgments_overlap_generation_and_completed_work_is_never_repeated():
    import threading

    from jev_benchmark.models import Comparison
    from jev_benchmark.queue import run_queue

    q, a, b = sample()
    c = BenchmarkModel.objects.create(name="C", provider="Lab", openrouter_id="lab/c")
    judged = threading.Event()

    def generate(model, question, **kwargs):
        if model == c:
            assert judged.wait(3), "Judge waited for all generation to finish"
        return {
            "text": "ok",
            "request": {},
            "response": {"usage": {"cost": 0}},
            "duration_ms": 1,
        }

    def judge(match):
        judged.set()
        return {
            "choice": "A",
            "confidence": 0.8,
            "probabilities": {"A": 0.8, "B": 0.2},
            "request": {},
            "response": {},
            "duration_ms": 1,
        }

    with (
        patch("jev_benchmark.queue.generate", side_effect=generate) as gen,
        patch("jev_benchmark.queue.judge", side_effect=judge) as j,
        patch("jev_benchmark.queue.CreditBudget", return_value=None),
    ):
        run_queue(workers=3)
        before = list(Answer.objects.values())
        matches = list(Comparison.objects.values())
        run_queue(workers=3)
        assert gen.call_count == 3 and j.call_count == 3
        assert before == list(Answer.objects.values())
        assert matches == list(Comparison.objects.values())


def test_attempt_cost_survives_retry_but_public_cost_is_success_only():
    from jev_benchmark.clients import ProviderError
    from jev_benchmark.models import WorkAttempt
    from jev_benchmark.queue import run_queue

    q, a, b = sample()
    b.active = False
    b.save()
    failure = ProviderError(
        "Capacity", kind="transient", audit={"response": {"usage": {"cost": 0.01}}}
    )
    success = {
        "text": "ok",
        "request": {},
        "response": {"usage": {"cost": 0.02}},
        "duration_ms": 1,
    }
    with (
        patch("jev_benchmark.queue.generate", side_effect=[failure, success]),
        patch("jev_benchmark.queue.CreditBudget", return_value=None),
    ):
        run_queue()
        Answer.objects.update(next_attempt_at=timezone.now())
        run_queue()
    assert list(
        WorkAttempt.objects.order_by("number").values_list("cost_usd", flat=True)
    ) == [Decimal("0.01"), Decimal("0.02")]
    assert leaderboard()["overall"][0]["cost_usd"] == Decimal("0.02")


def test_interrupted_attempt_is_not_automatically_regenerated():
    from jev_benchmark.models import WorkAttempt
    from jev_benchmark.queue import run_queue

    q, a, b = sample()
    b.active = False
    b.save()
    answer = Answer.objects.create(model=a, question=q, attempts=1)
    WorkAttempt.objects.create(answer=answer, number=1)
    with patch("jev_benchmark.queue.generate") as gen:
        run_queue()
    gen.assert_not_called()
    answer.refresh_from_db()
    assert answer.error_kind == "ambiguous"
    assert WorkAttempt.objects.get().status == "uncertain"


def test_backfill_is_idempotent_and_never_estimates_missing_cost():
    from django.core.management import call_command

    from jev_benchmark.models import WorkAttempt

    q, a, b = sample()
    Answer.objects.create(
        model=a,
        question=q,
        attempts=3,
        status="complete",
        response={"usage": {"cost": 0}},
    )
    Answer.objects.create(model=b, question=q, attempts=1, status="failed")
    call_command("backfill_jev_costs")
    call_command("backfill_jev_costs")
    assert WorkAttempt.objects.count() == 2
    assert WorkAttempt.objects.get(answer__model=a).cost_usd == Decimal(0)
    assert WorkAttempt.objects.get(answer__model=b).cost_usd is None
    assert WorkAttempt.objects.filter(number=2).count() == 0


def test_credit_reservations_stop_before_threshold():
    from jev_benchmark.budget import CreditBudget

    data = [
        {"total_credits": 50, "total_usage": 17.9},
        {"usage": 17.9, "limit_remaining": None},
        [{"id": "lab/a", "pricing": {"prompt": "0", "completion": "0.0001"}}],
    ]
    q, a, b = sample()
    with patch("jev_benchmark.budget.get_data", side_effect=data):
        budget = CreditBudget()
    assert not budget.fits(budget.estimate(a, q, 1024), Decimal(0))
    assert budget.fits(Decimal("0.05"), Decimal(0))
    assert not budget.fits(Decimal("0.05"), Decimal("0.06"))


def test_versioned_reasoning_settings_are_frozen_after_use():
    from django.core.exceptions import ValidationError

    q, a, b = sample()
    q.generation_max_tokens = 16384
    q.reasoning_effort = "medium"
    q.save()
    Answer.objects.create(model=a, question=q)
    q.reasoning_effort = "low"
    with pytest.raises(ValidationError):
        q.save()


def test_historical_snapshot_recovers_actual_retry_cost_without_changing_result(
    tmp_path,
):
    import json

    from django.core.management import call_command

    from jev_benchmark.models import WorkAttempt

    q, a, b = sample()
    row = Answer.objects.create(
        model=a,
        question=q,
        attempts=2,
        status="complete",
        text="preserved",
        response={"id": "new", "usage": {"cost": 0.02}},
    )
    before = Answer.objects.values().get(pk=row.pk)
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps(
            [
                {
                    "model": "jev_benchmark.answer",
                    "pk": row.pk,
                    "fields": {
                        "model": a.pk,
                        "question": q.pk,
                        "attempts": 1,
                        "status": "failed",
                        "response": {"id": "old", "usage": {"cost": 0.01}},
                        "updated_at": timezone.now().isoformat(),
                    },
                }
            ]
        )
    )
    call_command("backfill_jev_costs", snapshot=[str(snapshot)])
    call_command("backfill_jev_costs", snapshot=[str(snapshot)])
    assert WorkAttempt.objects.count() == 2
    assert WorkAttempt.objects.get(number=1).cost_usd == Decimal("0.01")
    assert Answer.objects.values().get(pk=row.pk) == before


@pytest.mark.parametrize("watch", [False, True])
def test_worker_rejects_non_main_thread(watch):
    from concurrent.futures import ThreadPoolExecutor

    from django.core.management import call_command
    from django.core.management.base import CommandError

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(call_command, "work_jev_benchmark", watch=watch)
        with pytest.raises(CommandError, match="main thread"):
            future.result()
