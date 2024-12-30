from django.db import models


class Policy(models.Model):
    title = models.CharField(
        max_length=255, default="Privacy Policy"
    )
    content = models.TextField()  
    type = models.CharField(max_length=20)
    version = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.is_active:
            Policy.objects.filter(type=self.type).exclude(id=self.id).update(
                is_active=False
            )
        super(Policy, self).save(*args, **kwargs)
