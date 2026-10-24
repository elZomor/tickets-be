import random
from datetime import date

from django.db import transaction
from django.db.models import F
from django.http import Http404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from third_side.auth import ThirdSideJWTAuthentication
from third_side.i18n import clean_locale, localize, localize_tree
from third_side.models import AboutPage, Ad, SiteSettings, TermsVersion
from third_side.models.Ad import AD_SIZES
from third_side.models.ActivityLog import ActivityAction
from third_side.permissions import RequirePerm, model_perms
from third_side.services import audit
from third_side.views.audit_mixin import AuditedMixin
from third_side.site_serializers import (
    AdSerializer,
    ad_images,
    AboutSerializer,
    FooterSerializer,
    about_to_urls,
    footer_payload,
)


class AboutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = None

    def get(self, request):
        page = AboutPage.load()
        if not page.content:
            raise Http404
        lang = clean_locale(request.query_params.get('lang'))
        return Response(localize_tree(about_to_urls(page.content, request), lang))


def _save_audited(request, instance, apply, repr_):
    """Run `apply()` (which saves `instance`) and log the change."""
    with transaction.atomic():
        before = audit.snapshot(instance) if instance.pk else {}
        apply()
        audit.record(
            request,
            ActivityAction.UPDATE if before else ActivityAction.CREATE,
            instance,
            before,
            audit.snapshot(instance),
            repr_=repr_,
        )


class _EditorView(APIView):
    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated, RequirePerm]
    throttle_scope = 'third_side_write'


class AboutDocView(_EditorView):
    """GET/PUT about/doc: the whole About page with every locale, for the admin.

    `content` has the shape documented on AboutPage; images are URLs from
    POST /media (stored as keys).
    """

    serializer_class = AboutSerializer
    required_perms = {'get': 'view_aboutpage', 'put': 'change_aboutpage'}

    def _payload(self, page, request):
        return {'content': about_to_urls(page.content or {}, request)}

    def get(self, request):
        return Response(self._payload(AboutPage.load(), request))

    def put(self, request):
        serializer = AboutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        page = AboutPage.load()

        def apply():
            page.content = serializer.validated_data['content']
            page.save()

        _save_audited(request, page, apply, 'About page')
        return Response(self._payload(page, request))


class FooterView(_EditorView):
    """GET/PUT footer: contact details, social links and sponsors (SiteSettings),
    every locale. The home hero in the same settings is left as it is."""

    serializer_class = FooterSerializer
    required_perms = {'get': 'view_sitesettings', 'put': 'change_sitesettings'}

    def get(self, request):
        return Response(footer_payload(SiteSettings.load(), request))

    def put(self, request):
        serializer = FooterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        site = SiteSettings.load()
        _save_audited(request, site, lambda: serializer.save_to(site), 'Footer')
        return Response(footer_payload(site, request))


def _terms_payload(terms, lang):
    return {
        'version': terms.version,
        'effective_date': terms.effective_date.isoformat(),
        **localize_tree(terms.content, lang),
    }


class TermsView(APIView):
    """The terms currently in force. Public: signup and social-login clients
    read it to show the text and to send back `accepted_terms_version`."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = None
    throttle_scope = 'third_side_read'

    def get(self, request):
        terms = TermsVersion.current()
        if terms is None:
            raise Http404
        return Response(
            _terms_payload(terms, clean_locale(request.query_params.get('lang')))
        )


class TermsVersionsView(APIView):
    """Every published version, newest first."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = None
    throttle_scope = 'third_side_read'

    def get(self, request):
        return Response(
            [
                {'version': t.version, 'effective_date': t.effective_date.isoformat()}
                for t in TermsVersion.published()
            ]
        )


class TermsDetailView(APIView):
    """One published version (old links, audit)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = None
    throttle_scope = 'third_side_read'

    def get(self, request, version):
        terms = TermsVersion.published().filter(version=version).first()
        if terms is None:
            raise Http404
        return Response(
            _terms_payload(terms, clean_locale(request.query_params.get('lang')))
        )


def _active_ads(lang, today):
    return [
        ad
        for ad in Ad.objects.filter(
            is_active=True, starts_at__lte=today, ends_at__gte=today
        )
        if lang in ad.locales
    ]


class AdPickView(APIView):
    """One weighted-random active ad for a locale and size, or 204.

    ?lang= ?size=tall|rect|wide ?exclude=1,2 (avoid repeating an ad on one page).
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = None

    def get(self, request):
        lang = clean_locale(request.query_params.get('lang'))
        size = request.query_params.get('size')
        if size not in AD_SIZES:
            return Response({'size': 'must be tall, rect or wide'}, status=400)
        exclude = {
            int(part)
            for part in request.query_params.get('exclude', '').split(',')
            if part.strip().isdigit()
        }
        # An ad without a creative for this size and locale cannot fill the slot.
        active = [
            ad
            for ad in _active_ads(lang, date.today())
            if (ad.images.get(lang) or {}).get(size)
        ]
        pool = [ad for ad in active if ad.pk not in exclude]
        candidates = pool or active
        weighted = [ad for ad in candidates if ad.weight > 0]
        if not weighted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        ad = random.choices(weighted, weights=[a.weight for a in weighted])[0]
        images = ad_images({lang: ad.images.get(lang) or {}}, request)[lang]
        image = images.get(size) or ''
        return Response(
            {
                'id': ad.pk,
                'type': ad.type,
                'name': ad.name,
                'url': ad.url,
                'internal': ad.internal,
                'image': image,
                # Other creatives of the same ad (e.g. the wide banner uses rect on phones).
                'images': images,
                'alt': localize(ad.alt, lang),
            }
        )


class AdEventView(APIView):
    """Public first-party counters: POST ads/<id>/impression|click."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = None
    throttle_scope = 'third_side_read'
    field = 'impressions'

    def post(self, request, pk):
        updated = Ad.objects.filter(pk=pk, is_active=True).update(
            **{self.field: F(self.field) + 1}
        )
        if not updated:
            raise Http404
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdImpressionView(AdEventView):
    field = 'impressions'


class AdClickView(AdEventView):
    field = 'clicks'


class AdViewSet(AuditedMixin, ModelViewSet):
    """Editors manage the ads (all of them, with their counters):
    GET/POST ads, GET/PATCH/DELETE ads/<id>. Readers only see ads/pick."""

    queryset = Ad.objects.all()
    serializer_class = AdSerializer
    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated, RequirePerm]
    required_perms = model_perms('ad')
    # ads/pick and ads/<id>/impression|click are separate public routes.
    lookup_value_regex = r'\d+'
