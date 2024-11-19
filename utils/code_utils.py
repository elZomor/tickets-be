import os
import uuid
from datetime import datetime

from django.contrib.auth.models import User


def upload_to(instance, filename):
    name = instance.name.get('en')
    cast_name = instance.cast_name
    created_at = datetime.now().strftime('%Y-%m-%d')
    file_name = f"{name} - {cast_name} - {created_at}{os.path.splitext(filename)[1]}"
    return os.path.join('media', 'shows', 'poster', file_name)


def create_super_user() -> None:
    from hita.models import HITAMember, Status

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
    if not User.objects.filter(username='hita_admin').exists():
        hita_admin_user = User.objects.create(username='hita_admin')
        hita_admin_user.set_password("Hita@123")
        hita_admin_user.is_staff = True
        hita_admin_user.is_active = True
        hita_admin_user.save()
        HITAMember.objects.create(
            **{
                'user': hita_admin_user,
                'first_name': 'hita',
                'last_name': 'admin',
                'request_status': Status.APPROVED.value,
            }
        )


def fill_initial_data():
    from hita.models import TheaterRolesChoices, TheaterRole
    from django.contrib.auth.models import User, Group, Permission

    if TheaterRole.objects.count() == 0:
        TheaterRole.objects.bulk_create(
            [TheaterRole(name=name) for name in TheaterRolesChoices.values]
        )

    group, _ = Group.objects.get_or_create(name='HITA_ADMIN')

    permission = Permission.objects.get(codename='can_approve_member_requests')
    if not group.permissions.filter(id=permission.id).exists():
        view_permission = Permission.objects.get(codename='view_hitamember')
        group.permissions.add(*[permission, view_permission])
        User.objects.get(username='hita_admin').groups.add(group)


def get_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join(instance.performer.hita_member.user.username, filename)
