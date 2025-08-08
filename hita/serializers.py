from rest_framework import serializers

from config.constants import ENVIRONMENT
from config.settings import s3_storage
from hita.models import (
    Performer,
    HITAMember,
    Experience,
    TheaterRole,
    ContactDetail,
    Gallery,
    PublicChannel,
    ShowReel,
    Status,
)
from hita.models.Achievement import Achievement


def get_user_from_context(context):
    if not context or not context.user:
        return None
    return context.user

def get_url(url):
    if ENVIRONMENT == 'local':
        return f'http://localhost:8005{url}'
    url = s3_storage.url(url)
    return url.replace("http://", "https://")

class HITAMemberViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = HITAMember
        fields = [
            'username',
            'full_name',
            'nick_name',
            'department',
            'grade',
            'is_graduated',
            'is_post_grad',
            'year_of_graduation',
            'study_type',
            'location',
            'gender',
            'request_status',
            'has_performer',
        ]

    @staticmethod
    def get_reviewed_by(obj):
        return obj.reviewed_by.__str__()


class HITAMemberCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = HITAMember
        exclude = ['invitation_code']

    def validate(self, attrs):
        if HITAMember.objects.filter(user=attrs['user']).exists():
            raise serializers.ValidationError(
                {'user': "A record for this user already exists."}
            )
        return attrs


class ContactDetailsViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactDetail
        exclude = ['performer']


class GalleryViewSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    class Meta:
        model = Gallery
        exclude = ['performer']
    def get_file(self, obj):
        return get_url(obj.file.url)


class GalleryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        fields = ['performer', 'description', 'file', 'is_profile_picture']


class ShowReelViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShowReel
        exclude = ['performer']


class ShowReelCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShowReel
        fields = ['performer', 'file']


class TheaterRoleViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = TheaterRole
        fields = ['name']

    def to_representation(self, instance):
        return instance.name


class ExperienceViewSerializer(serializers.ModelSerializer):
    role = TheaterRoleViewSerializer(many=True)

    class Meta:
        model = Experience
        exclude = ['performer']


class ExperienceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        exclude = ['role']


class AchievementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = [
            'performer',
            'position',
            'field',
            'festival_name',
            'show_name',
            'year',
        ]


class PublicChannelCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicChannel
        fields = ['performer', 'channel_type', 'channel_info']


class PublicChannelViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicChannel
        exclude = ['performer']


class ContactDetailsCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactDetail
        fields = ['performer', 'contact_type', 'contact_info']


class AchievementViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        exclude = ['performer']


class PerformerViewAllSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    nick_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    total_experiences = serializers.SerializerMethodField()
    skills_tags = TheaterRoleViewSerializer(many=True)

    class Meta:
        model = Performer
        fields = [
            'username',
            'full_name',
            'nick_name',
            'department',
            'skills_tags',
            'biography',
            'profile_picture',
            'status',
            'gender',
            'open_for',
            'age',
            'height',
            'weight',
            'total_experiences',
        ]

    @staticmethod
    def get_username(obj):
        return obj.hita_member.user.username

    @staticmethod
    def get_nick_name(obj):
        return obj.hita_member.nick_name

    @staticmethod
    def get_full_name(obj):
        return obj.full_name

    @staticmethod
    def get_department(obj):
        return obj.hita_member.department

    def get_profile_picture(self, obj):
        return get_url(obj.profile_picture)

    @staticmethod
    def get_gender(obj):
        return obj.hita_member.gender

    @staticmethod
    def get_age(obj):
        return obj.age

    @staticmethod
    def get_total_experiences(obj):
        return obj.experiences.count()


class PerformerDataViewOneSerializer(PerformerViewAllSerializer):
    grade = serializers.SerializerMethodField()
    graduation_year = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    study_type = serializers.SerializerMethodField()
    is_post_grad = serializers.SerializerMethodField()

    class Meta:
        model = Performer
        fields = PerformerViewAllSerializer.Meta.fields + [
            'grade',
            'graduation_year',
            'age',
            'study_type',
            'height',
            'weight',
            'date_of_birth',
            'is_post_grad',
        ]

    @staticmethod
    def get_grade(obj):
        return obj.hita_member.grade

    @staticmethod
    def get_graduation_year(obj):
        return obj.hita_member.year_of_graduation

    @staticmethod
    def get_age(obj):
        return obj.age

    @staticmethod
    def get_study_type(obj):
        return obj.hita_member.study_type

    @staticmethod
    def get_is_post_grad(obj):
        return obj.hita_member.is_post_grad


class PerformerViewOneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Performer
        fields = [
            'performer',
            'experiences',
            'achievements',
            'contact_detail_protected',
            'gallery_protected',
            'contact_details',
            'gallery',
            'public_channels',
            'has_show_reel',
        ]

    performer = serializers.SerializerMethodField()
    contact_details = serializers.SerializerMethodField()
    gallery = serializers.SerializerMethodField()
    experiences = serializers.SerializerMethodField()
    achievements = AchievementViewSerializer(many=True)
    public_channels = PublicChannelViewSerializer(many=True)
    has_show_reel = serializers.SerializerMethodField()

    @staticmethod
    def get_performer(obj):
        return PerformerDataViewOneSerializer(obj).data

    @staticmethod
    def get_experiences(obj):
        experiences = obj.experiences.order_by('-year')
        return ExperienceViewSerializer(experiences, many=True).data

    def get_contact_details(self, obj):
        user = get_user_from_context(self.context.get('hita_member'))
        if not user or obj.hita_member.request_status != Status.APPROVED.value:
            return []
        return ContactDetailsViewSerializer(
            obj.get_contact_details(user), many=True
        ).data

    @staticmethod
    def get_gallery(obj):
        return GalleryViewSerializer(obj.get_gallery(), many=True).data

    @staticmethod
    def get_has_show_reel(obj):
        return obj.has_show_reel


class PerformerCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Performer
        fields = [
            'hita_member',
            'date_of_birth',
            'height',
            'weight',
            'status',
            'gallery_protected',
            'contact_detail_protected',
            'biography',
            'open_for',
        ]


class PerformerUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Performer
        fields = [
            'date_of_birth',
            'height',
            'status',
            'biography',
            'open_for',
        ]


class PerformerViewSerializer(serializers.ModelSerializer):
    hita_member = HITAMemberViewSerializer()
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
            'gallery_protected',
            'contact_detail_protected',
            'achievement',
            'skills_tags',
            'hita_member',
            'profile_picture',
            'experience',
            'contact_details',
            'gallery',
        ]

    contact_details = serializers.SerializerMethodField()
    gallery = serializers.SerializerMethodField()

    def get_contact_details(self, obj):
        user = get_user_from_context(self.context.get('hita_member'))
        if not user or obj.hita_member.request_status != Status.APPROVED.value:
            return []
        return ContactDetailsViewSerializer(
            obj.get_contact_details(user), many=True
        ).data

    @staticmethod
    def get_gallery(obj):
        return GalleryViewSerializer(obj.get_gallery(), many=True).data
