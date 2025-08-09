import os
import uuid
from datetime import datetime
from functools import wraps

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
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


def upload_to_show(instance, filename):
    instance_id = instance.id or "unassigned"
    cast_name = slugify(instance.cast_name or "unknown")
    created_at = datetime.now().strftime('%Y-%m-%d')
    ext = os.path.splitext(filename)[1]
    file_name = f"{instance_id}_{cast_name}_{created_at}{ext}"
    return os.path.join('media', 'shows', 'poster', file_name)


def upload_to_festival(instance, filename):
    instance_id = instance.id or "unassigned"
    created_at = datetime.now().strftime('%Y-%m-%d')
    file_name = f"{instance_id} - {created_at}{os.path.splitext(filename)[1]}"
    return os.path.join('media', 'festivals', 'poster', file_name)


def upload_to_publication(instance, filename):
    instance_id = instance.id or "unassigned"
    created_at = datetime.now().strftime('%Y-%m-%d')
    file_name = f"{instance_id} - {created_at}{os.path.splitext(filename)[1]}"
    return os.path.join('media', 'publications', file_name)


def upload_to_script(instance, filename):
    author = slugify(instance.author or "unknown", allow_unicode=True)
    title = slugify(instance.title or "untitled", allow_unicode=True)
    ext = os.path.splitext(filename)[1]
    file_name = f"{author}_{title}{ext}"
    return os.path.join('media', 'scripts', author, file_name)


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.doc', '.docx', '.pdf']
    if ext not in valid_extensions:
        raise ValidationError('Unsupported file extension. Allowed: .doc, .docx, .pdf')


def generate_invitation_code():
    return str(uuid.uuid4()).replace('-', '')[:20]


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

    existing_roles = set(TheaterRole.objects.values_list('name', flat=True))
    missing_roles = [
        TheaterRole(name=name)
        for name in TheaterRolesChoices.values
        if name not in existing_roles
    ]

    if missing_roles:
        TheaterRole.objects.bulk_create(missing_roles)

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
    max_size_mb = 80
    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"File size must be less than {max_size_mb} MB")
