from rest_framework import serializers

from show.models import Show


class ShowViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Show
        fields = [
            'theater_id',
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
        ]

    theater_name = serializers.SerializerMethodField()
    theater_id = serializers.SerializerMethodField()
    show_date = serializers.SerializerMethodField()
    show_time = serializers.SerializerMethodField()
    booking_available = serializers.SerializerMethodField()

    @staticmethod
    def get_theater_name(obj):
        return obj.theater.__str__()

    @staticmethod
    def get_theater_id(obj):
        return obj.theater.pk

    @staticmethod
    def get_booking_available(obj):
        return obj.remaining_seats > 0 and obj.is_open

    @staticmethod
    def get_show_date(obj):
        return obj.time.strftime('%d-%b-%Y')

    @staticmethod
    def get_show_time(obj):
        return obj.time.strftime('%I:%M %p')
