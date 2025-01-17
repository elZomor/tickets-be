from datetime import datetime

from django.contrib import admin, messages

from hita.models import (
    Member,
    Performer,
    Experience,
    TheaterRole,
    ContactDetail,
    Gallery,
    Status,
    PublicChannel,
    ShowReel,
    Invitation, AdminMember,
)
from hita.models.Achievement import Achievement
from utils.email_utils import send_approve_email


@admin.register(AdminMember)
class AdminMemberAdmin(admin.ModelAdmin):
    pass

@admin.register(Member)
class HITAMemberAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'faculty',
        'department',
        'grade',
        'study_type',
        'is_graduated',
        'year_of_graduation',
        'request_status',
        'reviewed_by',
        'reviewed_at',
    ]
    list_filter = [
        'faculty',
        'grade',
        'location',
        'study_type',
        'is_graduated',
        'request_status',
    ]
    actions = ['approve_request', 'reject_request', 'block_member']

    def get_actions(self, request):
        actions = super().get_actions(request)
        hita_admin_actions = ['approve_request', 'reject_request', 'block_member']
        if request.user.groups.filter(name='MEMBER_ADMIN').exists():
            actions = {
                key: value
                for key, value in actions.items()
                if key in hita_admin_actions
            }
        elif not request.user.is_superuser:
            actions = {
                key: value
                for key, value in actions.items()
                if key not in hita_admin_actions
            }
        return actions

    @staticmethod
    @admin.display(description='Name')
    def name(obj):
        return obj

    @staticmethod
    def prevent_update_approved_members(func):
        def call(modeladmin, request, queryset, *args, **kwargs):
            hita_member = Member.objects.filter(user=request.user).last()
            if hita_member is None:
                modeladmin.message_user(
                    request,
                    'You can not perform this action because you are not HITA member.',
                    level=messages.ERROR,
                )
                return
            if (
                queryset.filter(request_status=Status.APPROVED.value).first()
                is not None
                and func.__name__ != 'block_member'
            ):
                modeladmin.message_user(
                    request,
                    'You can not change state of approved member.',
                    level=messages.ERROR,
                )
                return
            result = func(modeladmin, request, queryset, hita_member, *args, **kwargs)
            return result

        return call

    @staticmethod
    @admin.action(description='Approve request')
    @prevent_update_approved_members
    def approve_request(modeladmin, request, queryset, hita_member):
        approved_members = list(queryset)
        updated_count = queryset.update(
            request_status=Status.APPROVED.value,
            reviewed_by=hita_member,
            reviewed_at=datetime.now(),
        )
        for member in approved_members:
            send_approve_email.delay(to_email=member.user.email)
        modeladmin.message_user(request, f'{updated_count} items marked as approved.')

    @staticmethod
    @admin.action(description='Reject request')
    @prevent_update_approved_members
    def reject_request(modeladmin, request, queryset, hita_member):
        updated_count = queryset.update(
            request_status=Status.REJECTED.value,
            reviewed_by=hita_member,
            reviewed_at=datetime.now(),
        )
        modeladmin.message_user(request, f'{updated_count} items marked as rejected.')

    @staticmethod
    @admin.action(description='Block member')
    @prevent_update_approved_members
    def block_member(modeladmin, request, queryset, hita_member):
        updated_count = queryset.update(
            request_status=Status.BLOCKED.value,
            reviewed_by=hita_member,
            reviewed_at=datetime.now(),
        )
        modeladmin.message_user(request, f'{updated_count} items marked as blocked.')


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    pass


@admin.register(TheaterRole)
class TheaterRolesAdmin(admin.ModelAdmin):
    pass


class ExperienceInline(admin.StackedInline):
    model = Experience
    extra = 0


class ContactDetailsInline(admin.StackedInline):
    model = ContactDetail
    extra = 0


class GalleryInline(admin.StackedInline):
    model = Gallery
    extra = 0


class ShowReelInline(admin.StackedInline):
    model = ShowReel
    extra = 0


class AchievementInline(admin.StackedInline):
    model = Achievement
    extra = 0


class PublicChannelInline(admin.StackedInline):
    model = PublicChannel
    extra = 0


@admin.register(ContactDetail)
class ContactDetailsAdmin(admin.ModelAdmin):
    pass


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    pass


@admin.register(Performer)
class PerformerAdmin(admin.ModelAdmin):
    inlines = [
        ShowReelInline,
        GalleryInline,
        ExperienceInline,
        ContactDetailsInline,
        AchievementInline,
        PublicChannelInline,
    ]
