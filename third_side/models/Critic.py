from django.db import models

from third_side.utils import upload_to_critic_photo


class Critic(models.Model):
    name = models.CharField(max_length=150)
    bio = models.TextField(null=True, blank=True)
    photo = models.ImageField(upload_to=upload_to_critic_photo, null=True, blank=True)

    def __str__(self):
        return self.name
