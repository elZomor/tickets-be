from datetime import datetime

from rest_framework import serializers

from config.constants import ENVIRONMENT
from show.models import Show, Festival, Publication, ShowDate
from show.models.Show import ShowStatus
from django.utils.timezone import localtime, make_aware, get_current_timezone


def get_url(url, request):
    if request:
        if ENVIRONMENT == 'local':
            return request.build_absolute_uri(url)
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
            'name',
            'cast_name',
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
            'show_description',
            'nearest_night',
            'show_dates',
        ]

    festival_name = serializers.SerializerMethodField()
    festival_id = serializers.SerializerMethodField()
    poster = serializers.SerializerMethodField()
    nearest_night = serializers.SerializerMethodField()
    show_dates = serializers.SerializerMethodField()

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

    @staticmethod
    def get_nearest_night(obj):
        return (
            ShowDateViewSerializer(obj.nearest_night).data
            if obj.nearest_night
            else None
        )

    @staticmethod
    def get_show_dates(obj):
        return ShowDateViewSerializer(
            obj.dates.all().order_by('date', 'time'), many=True
        ).data

    def get_poster(self, obj):
        if obj.poster:
            return get_url(obj.poster.url, self.context.get('request'))
        return None


class ShowDateViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShowDate
        fields = ['id', 'show_date', 'show_time', 'theater_name', 'theater_link']

    theater_name = serializers.SerializerMethodField()
    theater_link = serializers.SerializerMethodField()
    show_date = serializers.SerializerMethodField()
    show_time = serializers.SerializerMethodField()

    @staticmethod
    def get_show_date(obj):
        dt = datetime.combine(obj.date, obj.time)
        aware_dt = make_aware(dt, timezone=get_current_timezone())
        return localtime(aware_dt).strftime('%Y-%m-%d')

    @staticmethod
    def get_show_time(obj):
        dt = datetime.combine(obj.date, obj.time)
        aware_dt = make_aware(dt, timezone=get_current_timezone())
        return localtime(aware_dt).strftime('%I:%M %p')

    @staticmethod
    def get_theater_name(obj):
        return obj.theater.__str__()

    @staticmethod
    def get_theater_link(obj):
        return obj.theater.location


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
            'publications',
        ]

    shows = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    publications = serializers.SerializerMethodField()

    def get_shows(self, obj):
        shows_qs = obj.shows.filter(status=ShowStatus.APPROVED.value).order_by(
            '-dates__date'
        )
        return ShowViewSerializer(
            shows_qs, many=True, context={'request': self.context.get('request')}
        ).data

    def get_logo(self, obj):
        if obj.logo:
            return get_url(obj.logo.url, self.context.get('request'))
        return None

    def get_publications(self, obj):
        qs = obj.publications.all().order_by('-publication_date')
        return PublicationPreviewSerializer(qs, many=True, context=self.context).data
