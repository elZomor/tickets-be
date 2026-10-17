from django.http import Http404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from third_side.i18n import LOCALES, clean_locale, localize
from third_side.models import Article, Category, NavGroup, SiteSettings
from third_side.models.Article import ArticleStatus
from third_side.read_serializers import (
    ArticleReadSerializer,
    CategoryReadSerializer,
    NavGroupSerializer,
)

HOME_LATEST_COUNT = 6


def _published_articles():
    return (
        Article.objects.filter(is_hidden=False, status=ArticleStatus.PUBLISHED)
        .select_related('category', 'critic')
        .prefetch_related('translations', 'tags')
        .order_by('-published_at', '-id')
    )


def _localized_site(site, lang):
    hero = site.hero or {}
    contact = site.contact or {}
    return {
        'hero': {
            'image': hero.get('image'),
            'title': localize(hero.get('title'), lang),
            'subtitle': localize(hero.get('subtitle'), lang),
            'cta_url': localize(hero.get('cta_url'), lang),
        },
        'site': {
            'contact': {
                'email': contact.get('email', ''),
                'phone': contact.get('phone', ''),
                'address': localize(contact.get('address'), lang),
            },
            'social': site.social or [],
            'sponsors': [
                {
                    'id': s.get('id'),
                    'name': localize(s.get('name'), lang),
                    'url': s.get('url', ''),
                    'logo': s.get('logo'),
                }
                for s in (site.sponsors or [])
            ],
        },
    }


class HomeView(APIView):
    """Everything the landing page and the shared header/footer need."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = None

    def get(self, request):
        lang = clean_locale(request.query_params.get('lang'))
        ctx = {'request': request}
        categories = Category.objects.select_related('group').order_by('order', 'id')
        groups = NavGroup.objects.prefetch_related('categories').order_by('order', 'id')
        latest = _published_articles()[:HOME_LATEST_COUNT]
        return Response(
            {
                **_localized_site(SiteSettings.load(), lang),
                'categories': CategoryReadSerializer(
                    categories, many=True, context=ctx
                ).data,
                'nav_groups': NavGroupSerializer(groups, many=True, context=ctx).data,
                'latest_articles': ArticleReadSerializer(
                    latest, many=True, context=ctx
                ).data,
            }
        )


class CategoryPageView(APIView):
    """A category's landing: its info plus the featured article.

    The article list is GET /articles?category=<slug> (paginated).
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = None

    def get(self, request, slug):
        category = Category.objects.select_related('group').filter(slug=slug).first()
        if category is None:
            raise Http404
        ctx = {'request': request}
        articles = _published_articles().filter(category=category)
        featured = articles.filter(is_featured=True).first() or articles.first()
        return Response(
            {
                'category': CategoryReadSerializer(category, context=ctx).data,
                'featured': (
                    ArticleReadSerializer(featured, context=ctx).data
                    if featured
                    else None
                ),
                'locales': list(LOCALES),
            }
        )
