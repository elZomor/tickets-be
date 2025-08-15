from django.db import models
from pgvector.django import VectorField


class PerformerInsights(models.Model):
    performer = models.ForeignKey(
        "hita.Performer", on_delete=models.CASCADE, related_name="insights"
    )
    features = models.JSONField(default=dict, blank=True)
    role_stats = models.JSONField(default=dict, blank=True)
    vec_profile = VectorField(dimensions=1536, null=True, blank=True)
    vec_skills = VectorField(dimensions=1536, null=True, blank=True)
    source_version = models.CharField(max_length=32, blank=True, default="v1")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Insights for {self.performer.hita_member.username}"
