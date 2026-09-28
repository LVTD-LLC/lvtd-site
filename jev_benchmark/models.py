from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q


class FrozenInputs(models.Model):
    """Create a new entry/version rather than silently mixing benchmark inputs."""

    frozen_fields = ()

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if self.pk and self.answers.exists():
            previous = type(self).objects.get(pk=self.pk)
            changed = {
                field: "Already used. Create a new entry for changed benchmark inputs."
                for field in self.frozen_fields
                if getattr(self, field) != getattr(previous, field)
            }
            if changed:
                raise ValidationError(changed)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class BenchmarkModel(FrozenInputs):
    name = models.CharField(max_length=120)
    provider = models.CharField(max_length=80)
    openrouter_id = models.CharField(max_length=200, unique=True)
    active = models.BooleanField(default=True)
    max_tokens = models.PositiveIntegerField(
        default=8192, validators=[MinValueValidator(1024), MaxValueValidator(65536)]
    )
    frozen_fields = ("openrouter_id", "max_tokens")

    class Meta:
        ordering = ("provider", "name")

    def __str__(self):
        return self.name


class Question(FrozenInputs):
    CATEGORIES = [
        ("writing", "Writing"),
        ("coding", "Programming"),
        ("math", "Mathematics"),
        ("personal", "Personal advice"),
    ]
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    prompt = models.TextField(max_length=16000)
    rubric = models.TextField(max_length=8000)
    weight = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    active = models.BooleanField(default=True)
    judge_model = models.CharField(max_length=100, default="jev-1.13.0")
    frozen_fields = ("prompt", "rubric", "judge_model")

    class Meta:
        ordering = ("pk",)

    def __str__(self):
        return self.title


class WorkResult(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    status = models.CharField(max_length=10, choices=Status, default=Status.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    error = models.CharField(max_length=200, blank=True)
    request = models.JSONField(default=dict, blank=True)
    response = models.JSONField(default=dict, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Answer(WorkResult):
    model = models.ForeignKey(
        BenchmarkModel, on_delete=models.PROTECT, related_name="answers"
    )
    question = models.ForeignKey(
        Question, on_delete=models.PROTECT, related_name="answers"
    )
    text = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["model", "question"], name="jev_unique_answer"
            )
        ]

    def __str__(self):
        return f"{self.model} / {self.question}"


class Comparison(WorkResult):
    question = models.ForeignKey(
        Question, on_delete=models.PROTECT, related_name="comparisons"
    )
    left = models.ForeignKey(
        Answer, on_delete=models.PROTECT, related_name="left_matches"
    )
    right = models.ForeignKey(
        Answer, on_delete=models.PROTECT, related_name="right_matches"
    )
    a_is_left = models.BooleanField(default=True)
    choice = models.CharField(
        max_length=1, choices=[("A", "A"), ("B", "B")], blank=True
    )
    confidence = models.FloatField(null=True, blank=True)
    probabilities = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["left", "right"], name="jev_unique_pair"),
            models.CheckConstraint(
                condition=Q(left__lt=F("right")), name="jev_canonical_pair"
            ),
        ]

    def clean(self):
        super().clean()
        if self.left_id and self.right_id:
            if (
                self.left.question_id != self.question_id
                or self.right.question_id != self.question_id
            ):
                raise ValidationError("Both answers must belong to this question.")

    @property
    def winner_id(self):
        if self.status != self.Status.COMPLETE:
            return None
        return (
            self.left.model_id
            if (self.choice == "A") == self.a_is_left
            else self.right.model_id
        )

    def __str__(self):
        return f"{self.question} / {self.left.model} vs {self.right.model}"


class RunnerLease(models.Model):
    """A renewable cross-process lease; crashed runners expire after 20 minutes."""

    owner = models.CharField(max_length=36, blank=True)
    expires_at = models.DateTimeField()
