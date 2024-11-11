from datetime import datetime

from django.db import models
from django.contrib.auth.models import User


class Department(models.TextChoices):
    ACTING = 'ACTING', 'Acting And Directing'
    DRAMA = 'DRAMA', 'Drama And Criticism'
    DECOR = 'DECOR', 'Decor'


class StudyTypes(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    PARALLEL = 'PARALLEL', 'Parallel'


class HITAMember(models.Model):
    user = models.OneToOneField(to=User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    grade = models.IntegerField(choices=((1, 'First'),
                                         (2, 'Second'),
                                         (3, 'Third'),
                                         (4, 'Forth')), null=True, blank=True)
    department = models.CharField(max_length=10, choices=Department.choices,
                                  default=Department.ACTING.value)
    study_type = models.CharField(max_length=15, choices=StudyTypes, default=StudyTypes.NORMAL.value)
    is_graduated = models.BooleanField(default=False)
    year_of_graduation = models.IntegerField(null=True, blank=True)
    favorite_performers = models.ManyToManyField(to='hita.Performer', blank=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'
