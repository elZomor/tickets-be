import os
from datetime import date

import requests
from PIL import Image, ImageOps
from django.conf import settings
from django.db.models import (
    Q,
    Count,
    OuterRef,
    Subquery,
    BooleanField,
    Case,
    When,
    Value,
    IntegerField,
)
from django.db.transaction import atomic
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from config.constants import FE_URL, BE_URL
from hita.Exceptions import ResourceNotFound
from hita.models import (
    Performer,
    HITAMember,
    TheaterRole,
    Gallery,
)
from hita.permissions import IsHITAMemberPermission
from hita.serializers import (
    PerformerViewAllSerializer,
    PerformerViewOneSerializer,
    PerformerCreateSerializer,
    ExperienceCreateSerializer,
    AchievementCreateSerializer,
    ContactDetailsCreateSerializer,
    PublicChannelCreateSerializer,
    GalleryCreateSerializer,
)
from utils.Response import (
    get_successful_response,
    get_bad_request_response,
    get_already_exists_response,
    get_successful_creation_response,
    get_unauthorized_response,
    get_not_found_response,
)
from io import BytesIO
import base64


class PerformerViewSet(viewsets.ModelViewSet):
    model = Performer
    serializer_class = PerformerViewOneSerializer
    lookup_field = "username"

    def get_queryset(self):
        profile_picture_subquery = Gallery.objects.filter(
            performer=OuterRef('pk'), is_profile_picture=True
        ).values('is_profile_picture')[:1]
        return Performer.objects.all().annotate(
            has_profile_picture=Subquery(
                profile_picture_subquery, output_field=BooleanField()
            )
        ).order_by(
            Case(
                When(has_profile_picture=True, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            'hita_member__first_name',
            'hita_member__last_name',
        )

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsHITAMemberPermission()]

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {'hita_member__user__username': self.kwargs[lookup_url_kwarg]}
        obj = queryset.filter(**filter_kwargs).first()
        if not obj:
            raise ResourceNotFound(
                f'Performer profile with username: {self.kwargs[lookup_url_kwarg]} does not exist'
            )
        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer_context(self):
        context = super(PerformerViewSet, self).get_serializer_context()
        if not self.request.user.is_authenticated:
            context.update({'hita_member': None})
        else:
            hita_member = HITAMember.objects.filter(user=self.request.user).last()
            context.update({'hita_member': hita_member})
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        permissions = self.build_permissions(instance)
        return get_successful_response(data=serializer.data, permissions=permissions)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_data(request.query_params.copy())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PerformerViewAllSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=self.request.user).last()
        performer_data = request.data
        performer_data['hita_member'] = hita_member.id
        serializer = PerformerCreateSerializer(
            hita_member.performer, data=performer_data, partial=True
        )
        if not serializer.is_valid():
            return get_bad_request_response(
                data=serializer.errors, message='Data not updated successfully!'
            )
        serializer.save()
        if skills_tags := performer_data.get('skills_tags'):
            skills = TheaterRole.objects.filter(name__in=skills_tags)
            hita_member.performer.skills_tags.set(skills)
        return get_successful_response(message='Data updated successfully!')

    def create(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=request.user).last()
        if Performer.objects.filter(hita_member=hita_member).exists():
            return get_already_exists_response(
                message='Performer profile already exist'
            )
        try:
            performer = self.create_performer_with_data(request.data, hita_member)
            return get_successful_creation_response(
                message='Performer created successfully!',
                data={'username': performer.hita_member.user.username},
            )

        except ValidationError as e:
            return get_bad_request_response(data=e.detail)
        except Exception as e:
            return get_bad_request_response(data=str(e))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        permissions = self.build_permissions(instance)
        if 'CAN_EDIT' not in permissions:
            return get_unauthorized_response(
                message='You do not have permission to perform this action'
            )
        instance.delete()
        return get_successful_response(
            message='Performer account has been deleted successfully!'
        )

    @action(detail=False, methods=['POST'], url_path='gallery')
    def add_gallery(self, request, *args, **kwargs):
        files = request.FILES
        data = request.data
        hita_member = HITAMember.objects.filter(user=request.user).last()
        performer = Performer.objects.filter(hita_member=hita_member).last()
        if not performer:
            return get_not_found_response(message='No performer found')

        image_list = []
        for key, value in files.items():
            image_list.append(
                {
                    'performer': performer.id,
                    'description': data.get(f'{key[:1]}[description]'),
                    'file': data.get(f'{key[:1]}[file]'),
                    'is_profile_picture': data.get(f'{key[:1]}[isProfilePicture]'),
                }
            )
        serializer = GalleryCreateSerializer(data=image_list, many=True)
        if not serializer.is_valid():
            return get_bad_request_response(data=serializer.errors)
        serializer.save()
        return get_successful_response(data={'user': hita_member.user.username})

    @action(detail=True, methods=['GET'], url_path='profile-meta')
    def profile_meta(self, request, username=None):
        hita_member = get_object_or_404(HITAMember, user__username=username)
        performer: Performer = get_object_or_404(Performer, hita_member=hita_member)

        profile_picture_url = (
            f"{BE_URL}{performer.profile_picture}"
            if performer.profile_picture.startswith('/media')
            else performer.profile_picture)
        frontend_url = f"{FE_URL}/artists/{username}"

        padded_image_data = self.resize_and_pad_image(profile_picture_url, is_local=True)

        html_content = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta property="og:title" content="Profile of {performer.full_name}">
            <meta property="og:image" content="{padded_image_data}">
            <meta property="og:image:secure_url" content="{padded_image_data}">
            <meta property="og:image:width" content="1200">
            <meta property="og:image:height" content="630">
            <meta property="og:image:type" content="image/jpeg">
            <meta property="og:image:alt" content="Profile picture of {performer.full_name}">
            <meta property="og:type" content="profile">
            <meta property="og:url" content="{frontend_url}">

            <script>
                setTimeout(function() {{
                    window.location.href = "{frontend_url}";
                }}, 3000);
            </script>

            <noscript>
                <meta http-equiv="refresh" content="3; url={frontend_url}">
            </noscript>
        </head>
        <body>
            <p>Redirecting to <a href="{frontend_url}">{frontend_url}</a> in a few seconds...</p>
        </body>
        </html>"""

        return HttpResponse(html_content, content_type="text/html; charset=utf-8")

    def build_permissions(self, instance):
        permissions = {'VIEW_GALLERY', 'VIEW_CONTACT_DETAILS', 'CAN_EDIT'}
        if instance.hita_member.user.id == self.request.user.id:
            return permissions
        permissions.discard('CAN_EDIT')
        if instance.get_contact_details(user=self.request.user) is None:
            permissions.discard('VIEW_CONTACT_DETAILS')
        if instance.get_gallery() is None:
            permissions.discard('VIEW_GALLERY')
        return permissions

    def filter_data(self, query_params):
        query_params.pop('page', None)
        query_params.pop('page_size', None)
        queryset = self.get_queryset()

        if not len(query_params):
            return queryset
        filter_query = Q()
        if query_params.get('name'):
            name: str = query_params.pop('name')[0]
            if name.__contains__(' ') and len(name) > 1:
                splitted_name = name.split(' ')
                filter_query |= Q(hita_member__first_name__icontains=splitted_name[0])
                filter_query |= Q(hita_member__last_name__icontains=splitted_name[1])
            filter_query |= Q(hita_member__first_name__icontains=name)
            filter_query |= Q(hita_member__last_name__icontains=name)
            filter_query |= Q(hita_member__nick_name__icontains=name)
            filter_query |= Q(hita_member__user__username__icontains=name)
        if query_params.get('gender'):
            gender = query_params.pop('gender')
            filter_query &= Q(hita_member__gender__in=gender)
        if query_params.get('department'):
            department = query_params.pop('department')
            filter_query &= Q(hita_member__department__in=department)
        if query_params.get('skills'):
            skills = query_params.pop('skills')
            queryset = queryset.annotate(
                num_required_skills=Count(
                    'skills_tags', filter=Q(skills_tags__name__in=skills)
                )
            ).filter(num_required_skills=len(skills))
        if query_params.get('age_range_before', 0) != 0:
            age_range_after = date.today().year - int(
                query_params.pop('age_range_after')[0]
            )
            age_range_before = date.today().year - int(
                query_params.pop('age_range_before')[0]
            )
            filter_query &= Q(date_of_birth__year__gte=age_range_before)
            filter_query &= Q(date_of_birth__year__lte=age_range_after)
        if query_params.get('weight_range_before', 0) != 0:
            weight_range_after = int(query_params.pop('weight_range_after')[0])
            weight_range_before = int(query_params.pop('weight_range_before')[0])
            filter_query &= Q(weight__gte=weight_range_after)
            filter_query &= Q(weight__lte=weight_range_before)
        if query_params.get('height_range_before', 0) != 0:
            height_range_after = int(query_params.pop('height_range_after')[0])
            height_range_before = int(query_params.pop('height_range_before')[0])
            filter_query &= Q(height__gte=height_range_after)
            filter_query &= Q(height__lte=height_range_before)
        if query_params.get('experience_range_before', 0) != 0:
            experience_range_after = int(
                query_params.pop('experience_range_after', [0])[0]
            )
            experience_range_before = int(
                query_params.pop('experience_range_before')[0]
            )
            queryset = queryset.annotate(experiences_count=Count('experiences')).filter(
                Q(experiences_count__gte=experience_range_after)
                & Q(experiences_count__lte=experience_range_before)
            )

        profile_picture_subquery = Gallery.objects.filter(
            performer=OuterRef('pk'), is_profile_picture=True
        ).values('is_profile_picture')[:1]
        return (
            queryset.filter(filter_query)
            .distinct()
            .annotate(
                has_profile_picture=Subquery(
                    profile_picture_subquery, output_field=BooleanField()
                )
            )
            .order_by(
                Case(
                    When(has_profile_picture=True, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                ),
                'hita_member__first_name',
                'hita_member__last_name',
            )
        )

    @atomic
    def create_performer_with_data(self, data, hita_member):
        user = hita_member.user
        user.username = data.get('performer_data').pop('username')
        user.save()
        performer = self.create_performer(data.get('performer_data'), hita_member.id)
        data.get('experiences') and self.save_experiences(
            data.get('experiences'), performer.id
        )
        data.get('achievements') and self.save_achievements(
            data.get('achievements'), performer.id
        )
        data.get('contact_section') and self.save_contact_details(
            data.get('contact_section'), performer.id
        )
        data.get('public_links_section') and self.save_public_channels(
            data.get('public_links_section'), performer.id
        )
        return performer

    @staticmethod
    def resize_and_pad_image(image_url, is_local, target_width=1200, target_height=630):
        """
        If the image is local, load it from MEDIA_ROOT instead of fetching via HTTP.
        Resizes while maintaining aspect ratio and adds white padding to 1200x630 px.
        Returns a base64-encoded image.
        """
        image_path = image_url.split("media/", 1)[-1]
        if os.path.exists(f'resized/{image_path}'):
            return f"{BE_URL}/media/resized/{image_path}"
        image = None

        # Check if image is hosted or local
        if not is_local:  # Remote image
            try:
                response = requests.get(image_url, timeout=5)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
            except requests.RequestException:
                return image_url  # Return original if request fails
        else:  # Local file (Django MEDIA_ROOT)
            local_path = os.path.join(settings.MEDIA_ROOT, image_path)
            if os.path.exists(local_path):
                image = Image.open(local_path)

        if image is None:
            return image_url  # Fallback to original image

        # Convert to RGB (fixes transparency issues with PNGs)
        image = image.convert("RGB")

        # Resize while maintaining aspect ratio
        image.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)

        # Create a white background canvas
        new_image = Image.new("RGB", (target_width, target_height), (255, 255, 255))

        # Center the resized image on the white background
        x_offset = (target_width - image.width) // 2
        y_offset = (target_height - image.height) // 2
        new_image.paste(image, (x_offset, y_offset))

        # Save the resized image temporarily
        resized_filename = f"resized/{image_path}"
        resized_path = os.path.join(settings.MEDIA_ROOT, resized_filename)
        os.makedirs(os.path.dirname(resized_path), exist_ok=True)
        new_image.save(resized_path, format="JPEG")

        # Return the new public image URL
        return f"{BE_URL}/media/{resized_filename}"
    @staticmethod
    def create_performer(performer_data, hita_member_id):
        performer_data['hita_member'] = hita_member_id
        serializer = PerformerCreateSerializer(data=performer_data)
        serializer.is_valid(raise_exception=True)
        performer = serializer.save()
        if performer_data.get('skills_tags'):
            skills = TheaterRole.objects.filter(
                name__in=performer_data.get('skills_tags')
            )
            performer.skills_tags.add(*skills)
        return performer

    @staticmethod
    def save_experiences(experiences, performer_id):
        for experience in experiences:
            experience_roles = experience.pop('roles')
            experience['performer'] = performer_id
            experience_serializer = ExperienceCreateSerializer(data=experience)
            experience_serializer.is_valid(raise_exception=True)
            saved_experience = experience_serializer.save()
            if experience_roles:
                experience_db_roles = TheaterRole.objects.filter(
                    name__in=experience_roles
                )
                saved_experience.role.add(*experience_db_roles)

    @staticmethod
    def save_achievements(achievements, performer_id):
        for achievement in achievements:
            achievement['performer'] = performer_id
            achievement_serializer = AchievementCreateSerializer(data=achievement)
            achievement_serializer.is_valid(raise_exception=True)
            achievement_serializer.save()

    @staticmethod
    def save_contact_details(contact_details, performer_id):
        for contact in contact_details:
            contact['performer'] = performer_id
            contact_details_serializer = ContactDetailsCreateSerializer(data=contact)
            contact_details_serializer.is_valid(raise_exception=True)
            contact_details_serializer.save()

    @staticmethod
    def save_public_channels(public_channels, performer_id):
        for channel in public_channels:
            channel['performer'] = performer_id
            public_channel_serializer = PublicChannelCreateSerializer(data=channel)
            public_channel_serializer.is_valid(raise_exception=True)
            public_channel_serializer.save()
