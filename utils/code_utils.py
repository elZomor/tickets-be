import os
import uuid
from datetime import datetime
from functools import wraps

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied


def get_hita_member_from_request(func):
    @wraps(func)
    def wrapper(viewset, request, *args, **kwargs):
        data = request.data
        from hita.models import HITAMember

        hita_member = HITAMember.objects.filter(user=request.user).last()
        data['performer'] = hita_member.performer.id
        request._full_data = data
        response = func(viewset, request, hita_member.performer, *args, **kwargs)
        return response

    return wrapper


def authorize_performer_data(func):
    @wraps(func)
    def wrapper(viewset, request, *args, **kwargs):
        from hita.models import HITAMember

        hita_member = HITAMember.objects.filter(user=request.user).last()
        queryset = viewset.get_queryset()
        instance = get_object_or_404(queryset, pk=kwargs.get('pk'))
        if instance.performer.id != hita_member.performer.id:
            raise PermissionDenied("You are not authorized to access this resource.")
        response = func(viewset, request, hita_member.performer, *args, **kwargs)
        return response

    return wrapper


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


def validate_file_size(value):
    max_size_mb = 50
    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"File size must be less than {max_size_mb} MB")