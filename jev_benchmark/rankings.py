"""Replay stored decisions only: no API calls and no persisted, drifting ratings."""

import hashlib
from decimal import Decimal

from .costs import cost_summary, reported_cost
from .models import Answer, BenchmarkModel, Comparison, Question
from .value import decorate, scatter


def leaderboard():
    models = list(BenchmarkModel.objects.filter(active=True))
    questions = list(Question.objects.filter(active=True))
    model_ids = {m.pk for m in models}
    answers = list(
        Answer.objects.filter(
            model__in=models, question__in=questions, status="complete"
        ).select_related("model")
    )
    matches = list(
        Comparison.objects.filter(
            question__in=questions,
            left__model__in=models,
            right__model__in=models,
            status="complete",
        ).select_related("left__model", "right__model")
    )
    sections = []
    for question in questions:
        question_answers = {
            a.model_id: a for a in answers if a.question_id == question.pk
        }
        question_matches = [m for m in matches if m.question_id == question.pk]
        ratings = dict.fromkeys(model_ids, 1500.0)
        games = dict.fromkeys(model_ids, 0)
        wins = dict.fromkeys(model_ids, 0)
        confidence = dict.fromkeys(model_ids, 0.0)

        def order(match):
            ids = sorted(
                [match.left.model.openrouter_id, match.right.model.openrouter_id]
            )
            return hashlib.sha256("|".join(ids).encode()).hexdigest()

        for match in sorted(question_matches, key=order):
            a, b = match.left.model_id, match.right.model_id
            expected_a = 1 / (1 + 10 ** ((ratings[b] - ratings[a]) / 400))
            score_a = int(match.winner_id == a)
            delta = 32 * (score_a - expected_a)
            ratings[a] += delta
            ratings[b] -= delta
            wins[match.winner_id] += 1
            for model_id in (a, b):
                games[model_id] += 1
                confidence[model_id] += match.confidence
        rows = [
            {
                "model": m,
                "rating": ratings[m.pk] if games[m.pk] else None,
                "games": games[m.pk],
                "wins": wins[m.pk],
                "losses": games[m.pk] - wins[m.pk],
                "confidence": confidence[m.pk] / games[m.pk] if games[m.pk] else None,
                "answer": question_answers.get(m.pk),
                "cost_usd": reported_cost(question_answers[m.pk].response)
                if m.pk in question_answers
                else None,
                "complete": len(models) > 1
                and games[m.pk] == len(models) - 1
                and m.pk in question_answers,
            }
            for m in models
        ]
        rows.sort(
            key=lambda row: (
                row["rating"] is None,
                -(row["rating"] or 0),
                row["model"].name,
            )
        )
        sections.append(
            {
                "question": question,
                "rows": decorate(rows),
                "matches": question_matches,
                "answers_count": len(question_answers),
                "matches_count": len(question_matches),
                "expected_matches": len(models) * (len(models) - 1) // 2,
            }
        )
    overall = []
    for model in models:
        entries = [
            (
                section["question"].weight,
                next(r for r in section["rows"] if r["model"].pk == model.pk),
            )
            for section in sections
        ]
        complete = bool(entries) and all(row["complete"] for _, row in entries)
        overall.append(
            {
                "model": model,
                "complete": complete,
                "rating": sum(weight * row["rating"] for weight, row in entries)
                / sum(weight for weight, _ in entries)
                if complete
                else None,
                "mean_cost_usd": sum(
                    Decimal(weight) * row["cost_usd"] for weight, row in entries
                )
                / sum(weight for weight, _ in entries)
                if entries and all(row["cost_usd"] is not None for _, row in entries)
                else None,
                "questions_complete": sum(row["complete"] for _, row in entries),
                "answers_count": sum(row["answer"] is not None for _, row in entries),
                "games": sum(row["games"] for _, row in entries),
                "expected_games": len(questions) * max(len(models) - 1, 0),
                **cost_summary(a for a in answers if a.model_id == model.pk),
            }
        )
    overall.sort(
        key=lambda row: (not row["complete"], -(row["rating"] or 0), row["model"].name)
    )
    decorate(overall)
    return {
        "scatter": scatter(overall),
        "models": models,
        "sections": sections,
        "overall": overall,
        "question_count": len(questions),
        "model_count": len(models),
        "completed_answers": len(answers),
        "expected_answers": len(models) * len(questions),
        "completed_comparisons": len(matches),
        "expected_comparisons": len(questions) * len(models) * (len(models) - 1) // 2,
        "answer_costs": cost_summary(answers),
        "last_updated": max(
            (m.completed_at for m in matches if m.completed_at), default=None
        ),
    }
