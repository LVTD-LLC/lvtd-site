from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.utils import timezone

from jev_benchmark.models import (
    Answer,
    BenchmarkModel,
    Comparison,
    Question,
    RunnerLease,
)
from jev_benchmark.rankings import leaderboard
from jev_benchmark.runner import run_benchmark

pytestmark = pytest.mark.django_db


@pytest.fixture
def cohort():
    models = [
        BenchmarkModel.objects.create(
            name=f"Model {i}", provider=f"Lab {i}", openrouter_id=f"lab/model-{i}"
        )
        for i in range(3)
    ]
    questions = [
        Question.objects.create(
            title=f"Question {i}",
            slug=f"question-{i}",
            category="coding",
            prompt="Solve this.",
            rubric="Correctness.",
        )
        for i in range(2)
    ]
    return models, questions


def generated(*args):
    return {
        "text": "An answer <script>alert(1)</script>",
        "response": {"model": "test", "usage": {"total_tokens": 10}},
        "request": {"model": "test"},
        "duration_ms": 5,
    }


def judged(*args):
    return {
        "choice": "A",
        "confidence": 0.8,
        "probabilities": {"A": 0.9, "B": 0.1},
        "response": {"model": "jev-1.13.0"},
        "request": {"state": {}},
        "duration_ms": 5,
    }


@patch("jev_benchmark.runner.judge", side_effect=judged)
@patch("jev_benchmark.runner.generate", side_effect=generated)
def test_incremental_round_robin(generate, judge, cohort):
    run_benchmark()
    assert generate.call_count == 6
    assert judge.call_count == 6
    assert Answer.objects.filter(status="complete").count() == 6
    assert Comparison.objects.filter(status="complete").count() == 6
    run_benchmark()
    assert generate.call_count == 6
    assert judge.call_count == 6
    BenchmarkModel.objects.create(name="New", provider="New", openrouter_id="new/model")
    run_benchmark()
    assert generate.call_count == 8
    assert judge.call_count == 12
    Question.objects.create(
        title="New question",
        slug="new",
        category="math",
        prompt="Prove this.",
        rubric="Rigour.",
    )
    run_benchmark()
    assert generate.call_count == 12
    assert judge.call_count == 18


@patch("jev_benchmark.runner.judge", side_effect=judged)
@patch("jev_benchmark.runner.generate", side_effect=generated)
def test_rankings_and_safe_public_page(generate, judge, cohort, client):
    run_benchmark()
    result = leaderboard()
    assert len(result["overall"]) == 3
    assert all(row["complete"] for row in result["overall"])
    assert result["completed_comparisons"] == 6
    assert result["expected_comparisons"] == 6
    page = client.get("/jev-benchmark")
    assert page.status_code == 200
    assert b"Jev Benchmark" in page.content
    detail = client.get("/jev-benchmark/question-0")
    assert detail.status_code == 200
    assert b"&lt;script&gt;" in detail.content
    assert b"<script>alert(1)</script>" not in detail.content
    assert client.get("/jev-benchamrk").status_code == 301
    assert client.post("/jev-benchmark").status_code == 405


@patch("jev_benchmark.runner.judge", side_effect=judged)
@patch("jev_benchmark.runner.generate", side_effect=generated)
def test_used_inputs_are_immutable(generate, judge, cohort):
    run_benchmark()
    question = cohort[1][0]
    question.prompt = "Changed"
    with pytest.raises(ValidationError):
        question.full_clean()
    question.refresh_from_db()
    question.weight = 2
    question.full_clean()
    question.save()
    model = cohort[0][0]
    model.openrouter_id = "different/model"
    with pytest.raises(ValidationError):
        model.full_clean()


def test_unique_pairs_and_same_question(cohort):
    models, questions = cohort
    a = Answer.objects.create(model=models[0], question=questions[0])
    b = Answer.objects.create(model=models[1], question=questions[0])
    c = Answer.objects.create(model=models[2], question=questions[1])
    Comparison.objects.create(question=questions[0], left=a, right=b)
    with pytest.raises(IntegrityError), transaction.atomic():
        Comparison.objects.create(question=questions[0], left=a, right=b)
    with pytest.raises(IntegrityError), transaction.atomic():
        Comparison.objects.create(question=questions[0], left=b, right=a)
    with pytest.raises(ValidationError):
        Comparison(question=questions[0], left=a, right=c).full_clean()


def test_lease_prevents_concurrent_paid_work(cohort):
    from datetime import timedelta

    RunnerLease.objects.create(
        pk=1, owner="other", expires_at=timezone.now() + timedelta(minutes=20)
    )
    with patch("jev_benchmark.runner.generate") as generate:
        with pytest.raises(RuntimeError, match="already running"):
            run_benchmark()
        generate.assert_not_called()


@patch("jev_benchmark.runner.judge", side_effect=judged)
@patch("jev_benchmark.runner.generate", side_effect=generated)
def test_failure_is_retried_without_repeating_successes(generate, judge, cohort):
    from jev_benchmark.clients import ProviderError

    generate.side_effect = [ProviderError("HTTP 503"), *[generated() for _ in range(5)]]
    result = run_benchmark()
    assert result["failed"] == 1
    assert Answer.objects.filter(status="failed").count() == 1
    assert judge.call_count == 4
    assert not all(row["complete"] for row in leaderboard()["overall"])
    generate.side_effect = generated
    run_benchmark()
    assert generate.call_count == 7
    assert judge.call_count == 6


def test_seed_and_dry_run_are_idempotent():
    call_command("seed_jev_benchmark")
    call_command("seed_jev_benchmark")
    assert BenchmarkModel.objects.count() == 10
    assert Question.objects.count() == 3
    with patch("jev_benchmark.runner.generate") as generate:
        call_command("run_jev_benchmark", dry_run=True)
        generate.assert_not_called()
    assert Answer.objects.count() == 0


@patch("jev_benchmark.runner.judge", side_effect=judged)
@patch("jev_benchmark.runner.generate", side_effect=generated)
def test_weighting_replays_without_paid_work(generate, judge, cohort):
    run_benchmark()
    before = leaderboard()
    first = cohort[1][0]
    first.weight = 3
    first.save()
    after = leaderboard()
    for row in after["overall"]:
        scores = [
            next(r["rating"] for r in s["rows"] if r["model"] == row["model"])
            for s in before["sections"]
        ]
        assert row["rating"] == pytest.approx((3 * scores[0] + scores[1]) / 4)
    assert generate.call_count == 6
    assert judge.call_count == 6
    # Readbacks do not depend on completion timestamps or query ordering.
    Comparison.objects.update(completed_at=timezone.now())
    assert [r["rating"] for r in leaderboard()["overall"]] == [
        r["rating"] for r in after["overall"]
    ]


def test_elo_expected_win_and_presentation_mapping(cohort):
    models, questions = cohort
    models[2].active = False
    models[2].save()
    questions[1].active = False
    questions[1].save()
    a = Answer.objects.create(
        model=models[0], question=questions[0], status="complete", text="a"
    )
    b = Answer.objects.create(
        model=models[1], question=questions[0], status="complete", text="b"
    )
    Comparison.objects.create(
        question=questions[0],
        left=a,
        right=b,
        a_is_left=False,
        choice="B",
        confidence=0.8,
        status="complete",
        completed_at=timezone.now(),
    )
    result = leaderboard()
    assert result["overall"][0]["model"] == models[0]
    assert result["overall"][0]["rating"] == 1516
    assert result["overall"][1]["rating"] == 1484


@patch("jev_benchmark.runner.judge", side_effect=judged)
@patch("jev_benchmark.runner.generate", side_effect=generated)
def test_request_limit_and_expired_lease(generate, judge, cohort):
    from datetime import timedelta

    RunnerLease.objects.create(
        pk=1, owner="crashed", expires_at=timezone.now() - timedelta(seconds=1)
    )
    run_benchmark(max_requests=1)
    assert generate.call_count == 1
    assert judge.call_count == 0
    assert not RunnerLease.objects.get(pk=1).owner
    run_benchmark()
    assert generate.call_count == 6
    assert judge.call_count == 6


def test_http_contracts_and_no_model_labels(cohort, settings):
    from jev_benchmark.clients import generate, judge

    settings.OPENROUTER_JEVBENCHMARK_AI_API_KEY = "test-secret"
    settings.TYPESAFE_API_KEY = "test-secret"
    models, questions = cohort
    response = {
        "model": "test",
        "choices": [{"message": {"content": "Answer"}, "finish_reason": "stop"}],
    }
    with patch("jev_benchmark.clients.post_json", return_value=response):
        result = generate(models[0], questions[0])
    assert result["text"] == "Answer"
    assert result["request"]["messages"][0]["content"] == questions[0].prompt
    assert result["request"]["model"] == models[0].openrouter_id
    a = Answer.objects.create(model=models[0], question=questions[0], text="First")
    b = Answer.objects.create(model=models[1], question=questions[0], text="Second")
    match = Comparison.objects.create(
        question=questions[0], left=a, right=b, a_is_left=False
    )
    response = {
        "model": "jev-1.13.0",
        "answers": {
            "winner": {
                "type": "choice",
                "choice": "B",
                "confidence": 0.8,
                "probabilities": {"A": 0.1, "B": 0.9},
            }
        },
    }
    with patch("jev_benchmark.clients.post_json", return_value=response):
        result = judge(match)
    assert result["request"]["state"] == {
        "question": questions[0].prompt,
        "answer_a": "Second",
        "answer_b": "First",
    }
    assert result["choice"] == "B"
    assert "test-secret" not in str(result)


@pytest.mark.parametrize(
    "content,finish", [("", "stop"), ("Partial", "length"), (None, "stop")]
)
def test_incomplete_answers_not_accepted(cohort, content, finish):
    from jev_benchmark.clients import ProviderError, generate

    with patch(
        "jev_benchmark.clients.post_json",
        return_value={
            "choices": [{"message": {"content": content}, "finish_reason": finish}]
        },
    ):
        with pytest.raises(ProviderError):
            generate(cohort[0][0], cohort[1][0])


@pytest.mark.parametrize(
    "probabilities,confidence",
    [
        ({"A": 0.8, "B": 0.8}, 0.5),
        ({"A": float("nan"), "B": 0.2}, 0.5),
        ({"A": 0.8, "B": 0.2}, float("inf")),
        (["A", "B"], 0.5),
    ],
)
def test_malformed_judgments_not_accepted(cohort, probabilities, confidence):
    from jev_benchmark.clients import ProviderError, judge

    models, questions = cohort
    a = Answer.objects.create(model=models[0], question=questions[0], text="First")
    b = Answer.objects.create(model=models[1], question=questions[0], text="Second")
    match = Comparison.objects.create(question=questions[0], left=a, right=b)
    response = {
        "model": "jev-1.13.0",
        "answers": {
            "winner": {
                "type": "choice",
                "choice": "A",
                "probabilities": probabilities,
                "confidence": confidence,
            }
        },
    }
    with patch("jev_benchmark.clients.post_json", return_value=response):
        with pytest.raises(ProviderError):
            judge(match)


def test_bounded_rate_limit_retry_and_redacted_errors():
    from unittest.mock import Mock

    import requests

    from jev_benchmark.clients import ProviderError, post_json

    throttled = Mock(status_code=429, headers={"Retry-After": "3"})
    ok = Mock(status_code=200, ok=True)
    ok.json.return_value = {"model": "test"}
    with (
        patch(
            "jev_benchmark.clients.requests.post", side_effect=[throttled, ok]
        ) as post,
        patch("jev_benchmark.clients.time.sleep") as sleep,
    ):
        assert post_json("https://example.test", "secret", {}) == {"model": "test"}
    assert post.call_count == 2
    sleep.assert_called_once_with(3)
    with patch(
        "jev_benchmark.clients.requests.post",
        side_effect=requests.Timeout("secret private text"),
    ) as post:
        with pytest.raises(ProviderError) as error:
            post_json("https://example.test", "secret", {})
        assert "secret" not in str(error.value)
    assert post.call_count == 1


def test_admin_results_readonly_and_anon_cannot_access(client, admin_client, cohort):
    from django.urls import reverse

    models, questions = cohort
    answer = Answer.objects.create(model=models[0], question=questions[0])
    url = reverse("admin:jev_benchmark_answer_change", args=[answer.pk])
    assert client.get(url).status_code == 302
    page = admin_client.get(url)
    assert page.status_code == 200
    assert b'name="text"' not in page.content
    assert (
        admin_client.post(
            reverse("admin:jev_benchmark_answer_delete", args=[answer.pk])
        ).status_code
        == 403
    )


def test_billing_error_stops_run_and_releases_lease(cohort):
    from jev_benchmark.clients import FatalProviderError

    with patch(
        "jev_benchmark.runner.generate",
        side_effect=FatalProviderError("Provider HTTP 402"),
    ) as generate:
        with pytest.raises(RuntimeError, match="402"):
            run_benchmark()
    assert generate.call_count == 1
    assert Answer.objects.filter(status="failed").count() == 1
    assert RunnerLease.objects.get(pk=1).owner == ""


def test_truncated_response_kept_for_audit_but_not_ranked(cohort):
    response = {
        "choices": [
            {"message": {"content": "Partial answer"}, "finish_reason": "length"}
        ]
    }
    with patch("jev_benchmark.clients.post_json", return_value=response):
        result = run_benchmark(max_requests=1)
    answer = Answer.objects.get()
    assert result["failed"] == 1
    assert answer.text == "Partial answer"
    assert answer.response == response
    assert answer.request["model"] == cohort[0][0].openrouter_id
    assert leaderboard()["completed_answers"] == 0


def test_larger_budget_retry_only_targets_truncated_answers(cohort):
    models, questions = cohort
    completed = Answer.objects.create(
        model=models[0],
        question=questions[0],
        status="complete",
        text="Preserved",
        request={"max_tokens": 8192},
    )
    truncated = Answer.objects.create(
        model=models[1],
        question=questions[0],
        status="failed",
        response={"choices": [{"finish_reason": "length"}]},
        request={"max_tokens": 8192},
    )
    other_failure = Answer.objects.create(
        model=models[2],
        question=questions[0],
        status="failed",
        error="HTTP 503",
    )
    with (
        patch("jev_benchmark.runner.generate", return_value=generated()) as generate,
        patch("jev_benchmark.runner.judge", side_effect=judged),
    ):
        run_benchmark(retry_max_tokens=16384)
    assert generate.call_args_list[0].args == (models[1], questions[0])
    assert generate.call_args_list[0].kwargs == {"max_tokens": 16384}
    assert generate.call_args_list[1].args == (models[2], questions[0])
    assert generate.call_args_list[1].kwargs == {}
    assert all(not call.kwargs for call in generate.call_args_list[2:])
    completed.refresh_from_db()
    assert completed.text == "Preserved"
    assert completed.request == {"max_tokens": 8192}
    assert completed.attempts == 0
    truncated.refresh_from_db()
    other_failure.refresh_from_db()
    assert truncated.status == other_failure.status == "complete"


def test_explicit_retry_budget_is_recorded(cohort):
    from jev_benchmark.clients import generate

    response = {
        "choices": [
            {"message": {"content": "Complete answer"}, "finish_reason": "stop"}
        ]
    }
    with patch("jev_benchmark.clients.post_json", return_value=response):
        result = generate(cohort[0][0], cohort[1][0], max_tokens=16384)
    assert result["request"]["max_tokens"] == 16384
    assert cohort[0][0].max_tokens == 8192


@pytest.mark.parametrize("budget", [0, 1023, 16385])
def test_retry_budget_rejects_out_of_range_without_api_calls(budget):
    with patch("jev_benchmark.runner.generate") as generate:
        with pytest.raises(ValueError, match="Retry output budget"):
            run_benchmark(retry_max_tokens=budget)
        generate.assert_not_called()


def test_question_shows_actual_retry_budget(cohort, client):
    models, questions = cohort
    Answer.objects.create(
        model=models[0],
        question=questions[0],
        status="complete",
        text="Final response",
        request={"max_tokens": 16384},
    )
    page = client.get("/jev-benchmark/question-0")
    assert b"Output budget: 16384 tokens" in page.content


def test_missing_request_budget_is_labelled_not_recorded(cohort, client):
    models, questions = cohort
    Answer.objects.create(
        model=models[0],
        question=questions[0],
        status="complete",
        text="Older response",
        request={},
    )
    page = client.get("/jev-benchmark/question-0")
    assert page.status_code == 200
    assert b"Output budget: not recorded" in page.content
