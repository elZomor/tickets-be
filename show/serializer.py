from rest_framework import serializers

from config.constants import ENVIRONMENT
from show.models import Show, Festival, Publication
from show.models.Show import ShowStatus
from django.utils.timezone import localtime


def get_url(url, request):
    if request:
        url = request.build_absolute_uri(url)
    if ENVIRONMENT == 'local':
        return url
    return url.replace("http://", "https://")

class PublicationPreviewSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = Publication
        fields = ['file', 'publication_number', 'publication_date']

    def get_file(self, obj):
        return get_url(obj.file.url, self.context.get('request'))

class ShowViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Show
        fields = [
            'id',
            'theater_link',
            'name',
            'cast_name',
            'show_date',
            'show_time',
            'theater_name',
            'link',
            'poster',
            'author',
            'director',
            'tags',
            'cast',
            'crew',
            'notes',
            'is_open',
            'festival_name',
            'festival_id',
            'cast_note',
            'show_description'
        ]

    theater_name = serializers.SerializerMethodField()
    theater_link = serializers.SerializerMethodField()
    show_date = serializers.SerializerMethodField()
    show_time = serializers.SerializerMethodField()
    booking_available = serializers.SerializerMethodField()
    festival_name = serializers.SerializerMethodField()
    festival_id = serializers.SerializerMethodField()
    poster = serializers.SerializerMethodField()

    @staticmethod
    def get_theater_name(obj):
        return obj.theater.__str__()

    @staticmethod
    def get_theater_link(obj):
        return obj.theater.location

    @staticmethod
    def get_show_date(obj):
        return localtime(obj.time).strftime('%Y-%m-%d')

    @staticmethod
    def get_show_time(obj):
        return localtime(obj.time).strftime('%I:%M %p')

    @staticmethod
    def get_festival_name(obj):
        if obj.festival:
            return obj.festival.name
        return None

    @staticmethod
    def get_festival_id(obj):
        if obj.festival:
            return obj.festival.id
        return None

    def get_poster(self, obj):
        if obj.poster:
            return get_url(obj.poster.url, self.context.get('request'))
        return None


class FestivalViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Festival
        fields = [
            'id',
            'name',
            'start_date',
            'end_date',
            'organizer',
            'jury_list',
            'awards',
            'extra_details',
            'logo',
            'festival_status',
            'organizing_team',
            'shows',
            'publications'
        ]

    shows = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    publications = serializers.SerializerMethodField()

    def get_shows(self, obj):
        shows_qs = obj.shows.filter(status=ShowStatus.APPROVED.value).order_by('time')
        return ShowViewSerializer(shows_qs, many=True, context={'request': self.context.get('request')}).data

    def get_logo(self, obj):
        if obj.logo:
            return get_url(obj.logo.url, self.context.get('request'))
        return None

    def get_publications(self, obj):
        qs = obj.publications.all().order_by('-publication_date')
        return PublicationPreviewSerializer(qs, many=True, context=self.context).data