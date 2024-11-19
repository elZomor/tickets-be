from rest_framework import serializers

from hita.models import (
    Performer,
    HITAMember,
    Experience,
    TheaterRole,
    ContactDetail,
    Gallery,
)
from hita.models.Achievement import Achievement


class HITAMemberViewSerializer(serializers.ModelSerializer):
    reviewed_by = serializers.SerializerMethodField()
    class Meta:
        model = HITAMember
        exclude = ['user', 'favorite_performers']
    @staticmethod
    def get_reviewed_by(obj):
        return obj.reviewed_by.__str__()

class HITAMemberCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    class Meta:
        model = HITAMember
        fields = '__all__'

    def validate(self, attrs):
        if HITAMember.objects.filter(user=attrs['user']).exists():
            raise serializers.ValidationError({'user': "A record for this user already exists."})
        return attrs


class ContactDetailsViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactDetail
        exclude = ['performer']


class GalleryViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        exclude = ['performer']


class TheaterRoleViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = TheaterRole
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
