from datetime import datetime

from django.contrib import admin, messages

from hita.models import (
    HITAMember,
    Performer,
    Experience,
    TheaterRole,
    ContactDetail,
    Gallery, Status,
)
from hita.models.Achievement import Achievement


@admin.register(HITAMember)
class HITAMemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'grade', 'department', 'location', 'study_type', 'is_graduated', 'year_of_graduation',
                    'request_status', 'reviewed_by', 'reviewed_at']
    list_filter = ['grade', 'location', 'study_type', 'is_graduated', 'request_status']
    actions = ['approve_request', 'reject_request', 'block_member']

    def get_actions(self, request):
        actions = super().get_actions(request)
        hita_admin_actions = ['approve_request', 'reject_request', 'block_member']
        if request.user.groups.filter(name='HITA_ADMIN').exists():
            actions = {key: value for key, value in actions.items() if key in hita_admin_actions}
        elif not request.user.is_superuser:
            actions = {key: value for key, value in actions.items() if key not in hita_admin_actions}
        return actions


    @staticmethod
    @admin.display(description='Name')
    def name(obj):
        return obj

    @staticmethod
    def prevent_update_approved_members(func):
        def call(modeladmin, request, queryset, *args, **kwargs):
            if queryset.filter(request_status=Status.APPROVED.value).first() is not None:
                modeladmin.message_user(request, 'You can not change state of approved member.', level=messages.ERROR)
                return
            result = func(modeladmin, request, queryset, *args, **kwargs)  # Call the original function
            return result

        return call

    @staticmethod
    @admin.action(description='Approve request')
    @prevent_update_approved_members
    def approve_request(modeladmin, request, queryset):
        updated_count = queryset.update(request_status=Status.APPROVED.value, reviewed_by=request.user,
                                        reviewed_at=datetime.now())
        modeladmin.message_user(request, f'{updated_count} items marked as approved.')

    @staticmethod
    @admin.action(description='Reject request')
    @prevent_update_approved_members
    def reject_request(modeladmin, request, queryset):
        updated_count = queryset.update(request_status=Status.REJECTED.value, reviewed_by=request.user,
                                        reviewed_at=datetime.now())
        modeladmin.message_user(request, f'{updated_count} items marked as rejected.')

    @staticmethod
    @admin.action(description='Block member')
    def block_member(modeladmin, request, queryset):
        updated_count = queryset.update(request_status=Status.BLOCKED.value, reviewed_by=request.user,
                                        reviewed_at=datetime.now())
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


class AchievementInline(admin.StackedInline):
    model = Achievement
    extra = 0


@admin.register(ContactDetail)
class ContactDetailsAdmin(admin.ModelAdmin):
    pass


@admin.register(Performer)
class PerformerAdmin(admin.ModelAdmin):
    inlines = [GalleryInline, ExperienceInline, ContactDetailsInline, AchievementInline]
