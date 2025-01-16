import uuid

from django.contrib.auth.models import User
from django.db import models


class Faculty(models.TextChoices):
    THEATER = 'THEATER_INST', 'Theater Institute'
    CINEMA = 'CINEMA_INST', 'Cinema Institute'


class TheaterDepartment(models.TextChoices):
    ACTING = 'ACTING_DEP', 'Acting And Directing'
    DRAMA = 'DRAMA_DEP', 'Drama And Criticism'
    DECOR = 'DECOR_DEP', 'Decor'
    TECH = 'TECH_DEP', 'Theatrical Techniques'


class CinemaDepartment(models.TextChoices):
    SCREENWRITING = 'SCREENWRITING_DEP', 'Screenwriting'
    CINEMATOGRAPHY = 'CINEMATOGRAPHY_DEP', 'CINEMATOGRAPHY'
    DIRECTING = 'DIRECTING_DEP', 'Directing'
    ANIMATION = 'ANIMATION_DEP', 'Animation'
    EDITING = 'EDITING_DEP', 'Editing'
    PRODUCTION = 'PRODUCTION_DEP', 'Production'
    SOUND_ENGINEERING = 'SOUND_ENGINEERING_DEP', 'Sound Engineering'
    SET_DESIGN = 'SET_DESIGN_DEP', 'Set Design'


class Department(models.TextChoices):
    @staticmethod
    def combined_choices():
        return TheaterDepartment.choices + CinemaDepartment.choices


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

class MemberType(models.TextChoices):
    STUDENT_MEMBER = 'STUDENT_MEMBER', 'Student Member'
    BUSINESS_MEMBER = 'BUSINESS_MEMBER', 'Business Member'


class AdminMember(models.Model):
    user = models.OneToOneField(to=User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    location = models.CharField(
        max_length=15, choices=Location.choices, default=Location.CAIRO.value
    )
    class Meta:
        permissions = [
            ('can_approve_all_member_requests', 'Can approve all member request'),
        ]

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

class AbstractMember(models.Model):
    user = models.OneToOneField(to=User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    nick_name = models.CharField(max_length=50, null=True, blank=True)
    favorite_performers = models.ManyToManyField(to='hita.Performer', blank=True)
    request_status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING.value
    )
    reviewed_by = models.ForeignKey(
        'hita.AdminMember',
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=(('M', 'Male'), ('F', 'Female')))
    invitation_code = models.CharField(max_length=20)
    location = models.CharField(
        max_length=15, choices=Location.choices, default=Location.CAIRO.value
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def full_name(self):
        return self.first_name + ' ' + self.last_name

    @property
    def username(self):
        return str(self.user)

    def save(self, *args, **kwargs):
        self.invitation_code = str(uuid.uuid4()).replace('-', '')[:20]
        super().save(*args, **kwargs)


class BusinessMember(AbstractMember):
    is_individual = models.BooleanField(default=False)
    casting_agency_name = models.CharField(max_length=50, null=True, blank=True)
    mobile_number = models.CharField(max_length=12, unique=True, null=True, blank=True)
    facebook_page = models.URLField(null=True, blank=True)


class Member(AbstractMember):
    grade = models.IntegerField(
        choices=((1, 'First'), (2, 'Second'), (3, 'Third'), (4, 'Forth')),
        null=True,
        blank=True,
    )
    faculty = models.CharField(
        max_length=20, choices=Faculty.choices, default=Faculty.THEATER.value
    )
    department = models.CharField(
        max_length=25,
        choices=Department.combined_choices(),
        default=TheaterDepartment.ACTING.value,
    )
    study_type = models.CharField(
        max_length=15, choices=StudyType.choices, default=StudyType.NORMAL.value
    )
    is_graduated = models.BooleanField(default=False)
    is_post_grad = models.BooleanField(default=False)
    year_of_graduation = models.IntegerField(null=True, blank=True)

    @property
    def has_performer(self):
        try:
            return self.performer is not None
        except Exception:
            return False
