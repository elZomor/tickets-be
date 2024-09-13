from django.contrib import admin

from clerk.models import ClerkUser


@admin.register(ClerkUser)
class ClerkUserAdmin(admin.ModelAdmin):
    fields = ['user', 'source', 'clerk_id']
