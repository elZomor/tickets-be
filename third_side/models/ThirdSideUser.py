from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone

from third_side.utils import AsciiUploadTo


class Role(models.TextChoices):
    EDITOR = 'EDITOR', 'Editor'
    READER = 'READER', 'Reader'


class ThirdSideUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('An email is required')
        user = self.model(email=email.strip().lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user


class ThirdSideUser(AbstractBaseUser):
    """A Third Side reader or editor, independent of django.contrib.auth.User.

    The app owns its accounts end to end (own table, own JWT realm, own auth
    endpoints) so it can be lifted into its own project and database: there
    it can simply become AUTH_USER_MODEL.
    """

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150, blank=True, default='')
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.READER)
    is_active = models.BooleanField(default=True)
    # Profile photo the reader uploads (POST /profile/me/avatar).
    avatar = models.ImageField(
        upload_to=AsciiUploadTo('third_side/avatars'), null=True, blank=True
    )
    # Email signature an editor sets in the admin (services/mail.signature_html):
    # {name: {ar, en}, title: {ar, en}, phone, show_photo, show_social}.
    signature = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    objects = ThirdSideUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        return self.name.strip() or self.email.split('@')[0]

    @property
    def is_editor(self):
        return self.role == Role.EDITOR
