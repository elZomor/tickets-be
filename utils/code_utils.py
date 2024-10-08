import os
from datetime import datetime

from django.contrib.auth.models import User


def upload_to(instance, filename):
    name = instance.name.get('en')
    cast_name = instance.cast_name
    created_at = datetime.now().strftime('%Y-%m-%d')
    file_name = f"{name} - {cast_name} - {created_at}{os.path.splitext(filename)[1]}"
    return os.path.join('media', 'shows', 'poster', file_name)


def create_super_user() -> None:
    if not User.objects.filter(is_superuser=True).exists():
        user: User = User.objects.filter(username="zomor").last()
        if not user:
            user = User.objects.create(
                username="zomor",
                is_staff=True,
                is_superuser=True,
                is_active=True,
            )
        user.set_password("zomor")
        user.save()
    if not User.objects.filter(username='test').exists():
        test_user = User.objects.create(username='test')
        test_user.set_password("Test@123")
        test_user.save()
