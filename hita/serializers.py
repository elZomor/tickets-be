from rest_framework import serializers

from hita.models import (
    Performer,
    HITAMember,
    Experience,
    TheaterRoles,
    ContactDetails,
    Gallery,
)
from hita.models.Achievement import Achievement


class HITAMemberViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = HITAMember
        fields = '__all__'


class ContactDetailsViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactDetails
        exclude = ['performer']


class GalleryViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        exclude = ['performer']


class TheaterRoleViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = TheaterRoles
        fields = ['name']


class ExperienceViewSerializer(serializers.ModelSerializer):
    role = TheaterRoleViewSerializer(many=True)

    class Meta:
        model = Experience
        exclude = ['performer']


class AchievementViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        exclude = ['performer']


class PerformerViewSerializer(serializers.ModelSerializer):
    hita_user = HITAMemberViewSerializer()
    experience = ExperienceViewSerializer(many=True)
    achievement = AchievementViewSerializer(many=True)
    skills_tags = TheaterRoleViewSerializer(many=True)

    class Meta:
        model = Performer
        fields = [
            'id',
            'age',
            'height',
            'status',
            'account_protected',
            'achievement',
            'skills_tags',
            'hita_user',
            'profile_picture',
            'experience',
            'contact_details',
            'gallery',
        ]

    contact_details = serializers.SerializerMethodField()
    gallery = serializers.SerializerMethodField()

    def get_contact_details(self, obj):
        return ContactDetailsViewSerializer(
            obj.get_contact_details(self.context.get('hita_member')), many=True
        ).data

    def get_gallery(self, obj):
        return GalleryViewSerializer(
            obj.get_gallery(self.context.get('hita_member')), many=True
        ).data
