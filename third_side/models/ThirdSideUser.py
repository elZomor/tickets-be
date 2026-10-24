from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import Group, Permission, PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone

from third_side.utils import AsciiUploadTo


APP_LABEL = 'third_side'


class ThirdSideUserManager(BaseUserManager):
    def with_perm(self, codename):
        """Active users holding a `third_side` permission: superusers, and
        members of a group (or holders of a direct grant) that carries it."""
        perm = Permission.objects.filter(
            content_type__app_label=APP_LABEL, codename=codename
        )
        return (
            self.filter(is_active=True)
            .filter(
                Q(is_superuser=True)
                | Q(groups__permissions__in=perm)
                | Q(user_permissions__in=perm)
            )
            .distinct()
        )

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('An email is required')
        user = self.model(email=email.strip().lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user


class ThirdSideUser(AbstractBaseUser, PermissionsMixin):
    """A Third Side reader or staff member, independent of django.contrib.auth.User.

    The app owns its accounts end to end (own table, own JWT realm, own auth
    endpoints) so it can be lifted into its own project and database: there
    it can simply become AUTH_USER_MODEL.

    Authorization is Django's own: a reader is a user with no group; staff get
    Groups (the roles, see services/roles.py) whose model permissions say what
    they can do. `has_perm` is answered here, not by ModelBackend, which only
    knows the project's AUTH_USER_MODEL.
    """

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150, blank=True, default='')
    # The shared django User also owns reverse accessors named `user_set`.
    groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name='third_side_users',
        related_query_name='third_side_user',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='third_side_users',
        related_query_name='third_side_user',
    )
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

    def permission_codenames(self):
        """Codenames of the `third_side` permissions held (all, for a superuser)."""
        if self.is_superuser:
            return sorted(
                Permission.objects.filter(
                    content_type__app_label=APP_LABEL
                ).values_list('codename', flat=True)
            )
        prefix = f'{APP_LABEL}.'
        return sorted(
            p.removeprefix(prefix)
            for p in self.get_all_permissions()
            if p.startswith(prefix)
        )

    def get_all_permissions(self, obj=None):
        """Every `app_label.codename` the user holds (cached on the instance)."""
        if not self.is_active:
            return set()
        if not hasattr(self, '_perm_cache'):
            perms = Permission.objects.filter(
                Q(third_side_user=self) | Q(group__third_side_user=self)
            ).values_list('content_type__app_label', 'codename')
            self._perm_cache = {f'{app}.{code}' for app, code in perms}
        return self._perm_cache

    def has_perm(self, perm, obj=None):
        if not self.is_active:
            return False
        return self.is_superuser or perm in self.get_all_permissions()

    def has_perms(self, perm_list, obj=None):
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        return self.is_active and (
            self.is_superuser
            or any(p.startswith(f'{app_label}.') for p in self.get_all_permissions())
        )
