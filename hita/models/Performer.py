from datetime import datetime

from django.db import models


class PerformerStatus(models.TextChoices):
    AVAILABLE = 'AVAILABLE', 'Available'
    UNAVAILABLE = 'UNAVAILABLE', 'Unavailable'


class OpenForEnum(models.TextChoices):
    FREE = 'FREE', 'Free'
    PAID = 'PAID', 'Paid'
    BOTH = 'BOTH', 'Both'


class Performer(models.Model):
    hita_member = models.OneToOneField(
        to='hita.HITAMember', on_delete=models.CASCADE, related_name='performer'
    )
    date_of_birth = models.DateField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    skills_tags = models.ManyToManyField('hita.TheaterRole', blank=True)
    status = models.CharField(
        max_length=20,
        choices=PerformerStatus.choices,
        default=PerformerStatus.AVAILABLE.value,
    )
    gallery_protected = models.BooleanField(default=False)
    contact_detail_protected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    white_list_members = models.ManyToManyField(
        'hita.HITAMember', related_name='white_list_members', blank=True
    )
    biography = models.CharField(max_length=300, null=True, blank=True)
    open_for = models.CharField(
        max_length=20,
        choices=OpenForEnum.choices,
        default=OpenForEnum.FREE.value,
    )

    @property
    def age(self):
        if not self.date_of_birth:
            return 0
        today = datetime.today()
        age = (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )
        return age

    @property
    def public_channels(self):
        return self.public_channel_list.all()

    @property
    def achievement(self):
        return self.achievements.all()

    @property
    def profile_picture(self):
        profile_picture = self.galleries.filter(is_profile_picture=True).last()
        if profile_picture:
            return profile_picture.file.url
        return 'https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png'

    def get_contact_details(self, user):
        if (
            not self.contact_detail_protected
            or self.white_list_members.filter(id=user.id).exists()
        ):
            return self.contact_detail_list.all()
        return None

    def get_gallery(self, user):
        if (
            not self.gallery_protected
            or self.white_list_members.filter(id=user.id).exists()
        ):
            return self.galleries.all()
        return None

    @property
    def full_name(self):
        return self.hita_member.first_name + ' ' + self.hita_member.last_name

    def __str__(self):
        return self.full_name
