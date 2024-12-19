from rest_framework import serializers

from hita.models import (
    Performer,
    HITAMember,
    Experience,
    TheaterRole,
    ContactDetail,
    Gallery,
    PublicChannel, ShowReel,
)
from hita.models.Achievement import Achievement


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
        fields = '__all__'

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
    class Meta:
        model = Gallery
        exclude = ['performer']


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
        fields = [
            'performer',
            'show_name',
            'director',
            'venue',
            'year',
            'duration',
            'show_type',
            'producer',
            'role_name',
            'role_brief',
        ]


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

    @staticmethod
    def get_profile_picture(obj):
        return obj.profile_picture

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
        return ContactDetailsViewSerializer(
            obj.get_contact_details(self.context.get('hita_member').user), many=True
        ).data

    def get_gallery(self, obj):
        return GalleryViewSerializer(
            obj.get_gallery(self.context.get('hita_member').user), many=True
        ).data

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
        return ContactDetailsViewSerializer(
            obj.get_contact_details(self.context.get('hita_member').user), many=True
        ).data

    def get_gallery(self, obj):
        return GalleryViewSerializer(
            obj.get_gallery(self.context.get('hita_member').user), many=True
        ).data
