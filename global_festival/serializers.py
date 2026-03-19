from rest_framework import serializers

from config.constants import ENVIRONMENT
from global_festival.models import Show
from global_festival.models.Article import Article
from global_festival.models.Comment import Comment
from global_festival.models.Festival import GlobalFestival
from global_festival.models.Reservation import Reservation


def build_media_url(file_field, request):
    """
    Mirror the behavior from the shows API so attachments return the absolute CDN URL.
    """
    if request and ENVIRONMENT == 'local':
        return request.build_absolute_uri(file_field.url)
    return f'https://media.play-cast.com/{file_field.name}?w=800&q=75&fmt=auto'


class GlobalFestivalSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalFestival
        fields = "__all__"

    total_shows = serializers.SerializerMethodField()
    total_articles = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()

    def get_total_shows(self, obj):
        return obj.total_shows

    def get_total_articles(self, obj):
        return obj.festival_articles.count()

    def get_logo(self, obj):
        if obj.logo:
            return build_media_url(obj.logo, self.context.get('request'))
        return None


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = "__all__"

    article_attachments_list = serializers.SerializerMethodField()

    def get_article_attachments_list(self, obj):
        request = self.context.get('request')
        attachments = obj.article_attachments.all().order_by('position')
        return [
            build_media_url(attachment.file, request)
            for attachment in attachments
            if attachment.file
        ]


class ShowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Show
        fields = "__all__"

    is_open_for_reservation = serializers.SerializerMethodField()
    festival_name = serializers.SerializerMethodField()
    festival_slug = serializers.SerializerMethodField()
    is_comment_allowed = serializers.SerializerMethodField()
    poster = serializers.SerializerMethodField()

    def get_is_open_for_reservation(self, obj):
        return obj.is_open_for_reservation

    def get_is_comment_allowed(self, obj):
        return obj.is_open_for_reservation

    def get_festival_name(self, obj: Show):
        return obj.festival.name if obj.festival else None

    def get_festival_slug(self, obj: Show):
        return obj.festival.start_date.year if obj.festival else None

    def get_poster(self, obj: Show):
        if obj.poster:
            return build_media_url(obj.poster, self.context.get('request'))
        return None


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = "__all__"


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['id', 'reservation_number', 'status', 'name', 'email', 'created_at']


class UserReservationSerializer(serializers.ModelSerializer):
    show_name = serializers.CharField(source='show.name')
    show_poster = serializers.SerializerMethodField()
    show_date = serializers.DateField(source='show.date')
    show_time = serializers.TimeField(source='show.time')
    venue_name = serializers.CharField(source='show.venue_name')
    festival_name = serializers.CharField(source='show.festival.name')
    festival_id = serializers.IntegerField(source='show.festival.pk')
    show_id = serializers.IntegerField(source='show.pk')

    class Meta:
        model = Reservation
        fields = [
            'id', 'reservation_number', 'status',
            'created_at', 'show_id', 'show_name', 'show_poster',
            'show_date', 'show_time', 'venue_name',
            'festival_name', 'festival_id',
        ]

    def get_show_poster(self, obj):
        if obj.show.poster:
            return build_media_url(obj.show.poster, self.context.get('request'))
        return None
