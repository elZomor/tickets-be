from rest_framework import serializers

from show.models import Show, Festival
from show.models.Show import ShowStatus
from django.utils.timezone import localtime


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
            'booking_available',
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
            'cast_note',
            'show_description'
        ]

    theater_name = serializers.SerializerMethodField()
    theater_link = serializers.SerializerMethodField()
    show_date = serializers.SerializerMethodField()
    show_time = serializers.SerializerMethodField()
    booking_available = serializers.SerializerMethodField()
    festival_name = serializers.SerializerMethodField()
    poster = serializers.SerializerMethodField()

    @staticmethod
    def get_theater_name(obj):
        return obj.theater.__str__()

    @staticmethod
    def get_theater_link(obj):
        return obj.theater.location

    @staticmethod
    def get_booking_available(obj):
        return obj.remaining_seats > 0 and obj.is_open

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

    def get_poster(self, obj):
        request = self.context.get('request')
        if obj.poster:
            url = obj.poster.url
            if request:
                url = request.build_absolute_uri(url)
            return url.replace("http://", "https://")
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
            'shows'
        ]

    shows = serializers.SerializerMethodField()

    def get_shows(self, obj):
        shows_qs = obj.shows.filter(status=ShowStatus.APPROVED.value).order_by('time')
        return ShowViewSerializer(shows_qs, many=True, context={'request': self.context.get('request')}).data
