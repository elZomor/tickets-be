from django.db import models
from django.contrib.auth.models import User


class Department(models.TextChoices):
    ACTING = 'ACTING', 'Acting And Directing'
    DRAMA = 'DRAMA', 'Drama And Criticism'
    DECOR = 'DECOR', 'Decor'


class StudyType(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    PARALLEL = 'PARALLEL', 'Parallel'


class Location(models.TextChoices):
    CAIRO = 'CAIRO', 'Cairo'
    ALEXANDRIA = 'ALEXANDRIA', 'Alexandria'


class Status(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    BLOCKED = 'BLOCKED', 'Blocked'


class HITAMember(models.Model):
    user = models.OneToOneField(to=User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    grade = models.IntegerField(
        choices=((1, 'First'), (2, 'Second'), (3, 'Third'), (4, 'Forth')),
        null=True,
        blank=True,
    )
    department = models.CharField(
        max_length=10, choices=Department.choices, default=Department.ACTING.value
    )
    study_type = models.CharField(
        max_length=15, choices=StudyType.choices, default=StudyType.NORMAL.value
    )
    is_graduated = models.BooleanField(default=False)
    year_of_graduation = models.IntegerField(null=True, blank=True)
    location = models.CharField(
        max_length=15, choices=Location.choices, default=Location.CAIRO.value
    )
    favorite_performers = models.ManyToManyField(to='hita.Performer', blank=True)
    request_status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING.value
    )
    reviewed_by = models.ForeignKey(
        'hita.HITAMember',
        on_delete=models.DO_NOTHING,
        related_name='reviewer',
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=(('M', 'Male'), ('F', 'Female')))

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        permissions = [
            ('can_approve_member_requests', 'Can approve member request'),
        ]
