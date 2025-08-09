from django.contrib.auth.models import User
from django.db import models

from utils.code_utils import upload_to_script, validate_file_extension


class ScriptStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    SPAM = 'SPAM', 'Spam'
    INAPPROPRIATE = 'INAPPROPRIATE', 'Inappropriate'


class Genre(models.TextChoices):
    DRAMA = 'DRAMA', 'Drama'
    COMEDY = 'COMEDY', 'Comedy'
    TRAGEDY = 'TRAGEDY', 'Tragedy'
    ROMANCE = 'ROMANCE', 'Romance'
    THRILLER = 'THRILLER', 'Thriller'
    FANTASY = 'FANTASY', 'Fantasy'
    SCIENCE_FICTION = 'SCIENCE_FICTION', 'Science Fiction'
    HORROR = 'HORROR', 'Horror'
    MYSTERY = 'MYSTERY', 'Mystery'
    ACTION = 'ACTION', 'Action'


class Script(models.Model):
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to=upload_to_script, validators=[validate_file_extension])
    author = models.CharField(max_length=50)
    status = models.CharField(
        choices=ScriptStatus.choices, default=ScriptStatus.PENDING.value, max_length=50
    )
    year = models.IntegerField(null=True, blank=True)
    genre = models.CharField(
        max_length=50, choices=Genre.choices, default=Genre.DRAMA.value
    )
    synopsis = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    cover = models.ImageField(upload_to=upload_to_script)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        to=User, on_delete=models.DO_NOTHING, related_name='script_created_by'
    )
    updated_by = models.ForeignKey(
        to=User, on_delete=models.DO_NOTHING, related_name='script_updated_by'
    )
    reviewed_by = models.ForeignKey(
        to=User, on_delete=models.DO_NOTHING, related_name='script_reviewed_by', null=True, blank=True
    )

    def __str__(self):
        return self.title
