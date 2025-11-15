from datetime import datetime, date as date_cls, time as time_cls

from rest_framework import serializers

from config.constants import ENVIRONMENT
from show.models import Show, Festival, Publication, ShowDate
from show.models.Show import ShowStatus
from django.utils.timezone import localtime, make_aware, get_current_timezone
from django.db.models import DateField, OuterRef, Prefetch, Subquery, TimeField, Value
from django.db.models.functions import Coalesce
import logging

logger = logging.getLogger("gunicorn.error")


def get_url(file, request):
    if request:
        if ENVIRONMENT == 'local':
            return request.build_absolute_uri(file.url)
    return f'https://media.play-cast.com/{file.name}?w=800&q=75&fmt=auto'


class PublicationPreviewSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = Publication
        fields = ['file', 'publication_number', 'publication_date']

    def get_file(self, obj):
        return get_url(obj.file, self.context.get('request'))


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
        if hasattr(obj, '_get_cached_dates'):
            dates = obj._get_cached_dates()
        else:
            dates = list(obj.dates.all())
        ordered_dates = sorted(dates, key=lambda d: (d.date, d.time))
        return ShowDateViewSerializer(ordered_dates, many=True).data

    def get_poster(self, obj: Show):
        if obj.poster:
            return get_url(obj.poster, self.context.get('request'))
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
    awards = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    publications = serializers.SerializerMethodField()

    def get_shows(self, obj):
        shows = getattr(obj, 'prefetched_shows', None)
        if shows is None:
            latest_date_sq = (
                ShowDate.objects.filter(show=OuterRef('pk'))
                .order_by('-date', '-time')
                .values('date')[:1]
            )
            latest_time_on_latest_sq = (
                ShowDate.objects.filter(
                    show=OuterRef('pk'),
                    date=Subquery(latest_date_sq),
                )
                .order_by('-time')
                .values('time')[:1]
            )
            shows = (
                obj.shows.filter(status=ShowStatus.APPROVED.value)
                .annotate(
                    latest_date=Coalesce(
                        Subquery(latest_date_sq, output_field=DateField()),
                        Value(date_cls.min, output_field=DateField()),
                    ),
                    latest_time=Coalesce(
                        Subquery(latest_time_on_latest_sq, output_field=TimeField()),
                        Value(time_cls.min, output_field=TimeField()),
                    ),
                )
                .prefetch_related(
                    'tags',
                    Prefetch(
                        'dates',
                        queryset=ShowDate.objects.select_related('theater').only(
                            'id',
                            'show_id',
                            'date',
                            'time',
                            'theater_id',
                            'theater__name',
                            'theater__location',
                        ),
                    ),
                )
                .order_by('-latest_date', '-latest_time')
            )
        return ShowViewSerializer(
            shows, many=True, context={'request': self.context.get('request')}
        ).data

    def get_logo(self, obj):
        if obj.logo:
            return get_url(obj.logo, self.context.get('request'))
        return None

    def get_publications(self, obj):
        qs = obj.publications.all().order_by('-publication_date')
        return PublicationPreviewSerializer(qs, many=True, context=self.context).data

    def get_awards(self, obj):
        awards_list = obj.awards
        final_awards_list = []
        for award_category in awards_list:
            category_list = []
            for category_list_item in award_category['children']:
                name = category_list_item.get('name')
                rank = category_list_item.get('rank')
                show = category_list_item.get('show')
                award_value = name
                if rank:
                    award_value += f' - {rank}'
                if show:
                    award_value += f' ({show})'
                category_list.append(award_value)
            final_awards_list.append(
                {'text': award_category['text'], 'children': category_list}
            )
        return final_awards_list
