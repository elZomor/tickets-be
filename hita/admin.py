from django.contrib import admin

from hita.models import (
    HITAMember,
    Performer,
    Experience,
    TheaterRoles,
    ContactDetails,
    Gallery,
)
from hita.models.Achievement import Achievement


@admin.register(HITAMember)
class HITAMemberAdmin(admin.ModelAdmin):
    pass


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    pass


@admin.register(TheaterRoles)
class TheaterRolesAdmin(admin.ModelAdmin):
    pass


class ExperienceInline(admin.StackedInline):
    model = Experience
    extra = 0


class ContactDetailsInline(admin.StackedInline):
    model = ContactDetails
    extra = 0


class GalleryInline(admin.StackedInline):
    model = Gallery
    extra = 0


class AchievementInline(admin.StackedInline):
    model = Achievement
    extra = 0


@admin.register(ContactDetails)
class ContactDetailsAdmin(admin.ModelAdmin):
    pass


@admin.register(Performer)
class PerformerAdmin(admin.ModelAdmin):
    inlines = [GalleryInline, ExperienceInline, ContactDetailsInline, AchievementInline]
