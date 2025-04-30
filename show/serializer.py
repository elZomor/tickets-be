from rest_framework import serializers

from show.models import Show


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
            'festival_name'
        ]

    theater_name = serializers.SerializerMethodField()
    theater_link = serializers.SerializerMethodField()
    show_date = serializers.SerializerMethodField()
    show_time = serializers.SerializerMethodField()
    booking_available = serializers.SerializerMethodField()
    festival_name = serializers.SerializerMethodField()

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
        return obj.time.strftime('%Y-%m-%d')

    @staticmethod
    def get_show_time(obj):
        return obj.time.strftime('%I:%M %p')

    @staticmethod
    def get_festival_name(obj):
        if obj.festival:
            return obj.festival.name
        return None

