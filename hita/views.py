import os

from django.db.models import Q
from django.http import StreamingHttpResponse
from rest_framework.exceptions import ValidationError
from django.db.transaction import atomic
from rest_framework import status
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import boto3

from config.storages import get_s3_object
from hita.Exceptions import ResourceNotFound
from hita.models import (
    Performer,
    HITAMember,
    Department,
    StudyType,
    Location,
    TheaterRole,
    ContactType,
    Experience,
    Achievement,
    PublicChannel,
    ContactDetail,
    Gallery,
    ShowReel,
)
from hita.permissions import IsHITAMemberPermission
from hita.serializers import (
    HITAMemberViewSerializer,
    HITAMemberCreateSerializer,
    PerformerViewAllSerializer,
    PerformerViewOneSerializer,
    PerformerCreateSerializer,
    ExperienceCreateSerializer,
    AchievementCreateSerializer,
    ContactDetailsCreateSerializer,
    PublicChannelCreateSerializer,
    GalleryCreateSerializer,
    ExperienceViewSerializer,
    AchievementViewSerializer,
    PublicChannelViewSerializer,
    ContactDetailsViewSerializer,
    GalleryViewSerializer,
    ShowReelCreateSerializer,
    ShowReelViewSerializer,
)
from utils.code_utils import get_hita_member_from_request, authorize_performer_data


class PerformerViewSet(viewsets.ModelViewSet):
    model = Performer
    queryset = Performer.objects.all().order_by(
        'hita_member__first_name', 'hita_member__last_name'
    )
    permission_classes = [IsHITAMemberPermission]
    serializer_class = PerformerViewOneSerializer

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
        hita_member = HITAMember.objects.filter(user=self.request.user).last()
        context.update({'hita_member': hita_member})
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        permissions = self.build_permissions(instance)
        return Response(
            data={
                'status': 'SUCCESS',
                'data': serializer.data,
                'permissions': permissions,
            },
            status=status.HTTP_200_OK,
        )

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
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'status': 'FAILED', 'message': 'Data not updated successfully!'},
            )
        serializer.save()
        if skills_tags := performer_data.get('skills_tags'):
            skills = TheaterRole.objects.filter(name__in=skills_tags)
            hita_member.performer.skills_tags.set(skills)
        return Response(
            status=status.HTTP_200_OK,
            data={'status': 'SUCCESS', 'message': 'Data updated successfully!'},
        )

    def create(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=request.user).last()
        if Performer.objects.filter(hita_member=hita_member).exists():
            return Response(
                data={'status': 'FAILED', 'message': 'Performer profile already exist'},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            self.create_performer_with_data(request.data, hita_member)
            return Response(
                data={'status': 'SUCCESS', 'message': 'Created Successfully!'},
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response(
                {'status': 'FAILED', 'data': e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {'status': 'FAILED', 'data': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        permissions = self.build_permissions(instance)
        if 'CAN_EDIT' not in permissions:
            return Response(
                data={'status': 'FAILED', 'message': 'Not Allowed'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        instance.delete()
        return Response(
            data={
                'status': 'SUCCESS',
                'message': 'Performer account has been deleted successfully!',
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['POST'], url_path='gallery')
    def add_gallery(self, request, *args, **kwargs):
        files = request.FILES
        data = request.data
        hita_member = HITAMember.objects.filter(user=request.user).last()
        performer = Performer.objects.filter(hita_member=hita_member).last()
        if not performer:
            return Response(
                data={'status': 'FAILED', 'message': 'No performer found'},
                status=status.HTTP_404_NOT_FOUND,
            )
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
            return Response(
                {'status': 'FAILED', 'data': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(
            data={'status': 'SUCCESS', 'data': {'user': hita_member.user.username}},
            status=status.HTTP_200_OK,
        )

    def build_permissions(self, instance):
        permissions = {'VIEW_GALLERY', 'VIEW_CONTACT_DETAILS', 'CAN_EDIT'}
        if instance.hita_member.user.id == self.request.user.id:
            return permissions
        permissions.discard('CAN_EDIT')
        if instance.get_contact_details(user=self.request.user) is None:
            permissions.discard('VIEW_CONTACT_DETAILS')
        if instance.get_gallery(user=self.request.user) is None:
            permissions.discard('VIEW_GALLERY')
        return permissions

    def filter_data(self, query_params):
        query_params.pop('page', None)
        query_params.pop('page_size', None)
        queryset = self.get_queryset()

        if not len(query_params):
            return queryset
        print(queryset, flush=True)
        filter_query = Q()
        if query_params.get('name'):
            name = query_params.pop('name')[0]
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
            filter_query &= Q(skills_tags__name__in=skills)
        return queryset.filter(filter_query).distinct()

    @atomic
    def create_performer_with_data(self, data, hita_member):
        user = hita_member.user
        user.username = data.get('performer_data').pop('username')
        user.save()
        performer = self.create_performer(data.get('performer_data'), hita_member.id)
        self.save_experiences(data.get('experiences'), performer.id)
        self.save_achievements(data.get('achievements'), performer.id)
        self.save_contact_details(data.get('contact_section'), performer.id)
        self.save_public_channels(data.get('public_links_section'), performer.id)

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


class ExperienceViewSet(viewsets.ModelViewSet):
    queryset = Experience.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = ExperienceCreateSerializer

    def create(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=self.request.user).last()
        experience_data = request.data
        experience_data['performer'] = hita_member.performer.id
        serializer = ExperienceCreateSerializer(data=experience_data)
        if not serializer.is_valid():
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'status': 'FAILED', 'message': 'Data not create successfully!'},
            )
        instance = serializer.save()
        if roles := experience_data.get('roles'):
            roles = TheaterRole.objects.filter(name__in=roles)
            instance.role.set(roles)
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                'status': 'SUCCESS',
                'message': 'Experience created successfully!',
                'data': {'id': instance.id},
            },
        )

    def list(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=self.request.user).last()
        experiences = hita_member.performer.experiences.all().order_by('-year')
        serializer = ExperienceViewSerializer(experiences, many=True)
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'Experience created successfully!',
                'data': serializer.data,
            },
        )

    @authorize_performer_data
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        instance = self.get_object()
        if roles := request.data.get('roles'):
            roles = TheaterRole.objects.filter(name__in=roles)
            instance.role.set(roles)
        return Response(
            status=status.HTTP_200_OK,
            data={'status': 'SUCCESS', 'message': 'Experience updated successfully!'},
        )

    @authorize_performer_data
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class AchievementViewSet(viewsets.ModelViewSet):
    queryset = Achievement.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = AchievementCreateSerializer

    def create(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=self.request.user).last()
        achievement_data = request.data
        achievement_data['performer'] = hita_member.performer.id
        serializer = self.get_serializer(data=achievement_data)
        if not serializer.is_valid():
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'status': 'FAILED', 'message': 'Data not create successfully!'},
            )
        instance = serializer.save()
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                'status': 'SUCCESS',
                'message': 'Achievement created successfully!',
                'data': {'id': instance.id},
            },
        )

    def list(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=self.request.user).last()
        achievements = hita_member.performer.achievements.all().order_by('-year')
        serializer = AchievementViewSerializer(achievements, many=True)
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'Achievement created successfully!',
                'data': serializer.data,
            },
        )

    @authorize_performer_data
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(
            status=status.HTTP_200_OK,
            data={'status': 'SUCCESS', 'message': 'Achievement updated successfully!'},
        )

    @authorize_performer_data
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class PublicChannelsViewSet(viewsets.ModelViewSet):
    queryset = PublicChannel.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = PublicChannelCreateSerializer

    @get_hita_member_from_request
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                'status': 'SUCCESS',
                'message': 'Channel created successfully!',
            },
        )

    @get_hita_member_from_request
    def list(self, request, performer, *args, **kwargs):
        channels = performer.public_channel_list.all()
        serializer = PublicChannelViewSerializer(channels, many=True)
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'Channel created successfully!',
                'data': serializer.data,
            },
        )

    @authorize_performer_data
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(
            status=status.HTTP_200_OK,
            data={'status': 'SUCCESS', 'message': 'Channel updated successfully!'},
        )

    @authorize_performer_data
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ContactDetailsViewSet(viewsets.ModelViewSet):
    queryset = ContactDetail.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = ContactDetailsCreateSerializer

    @get_hita_member_from_request
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                'status': 'SUCCESS',
                'message': 'Contact Detail created successfully!',
            },
        )

    @get_hita_member_from_request
    def list(self, request, performer, *args, **kwargs):
        contact_details = performer.get_contact_details(request.user).all()
        serializer = ContactDetailsViewSerializer(contact_details, many=True)
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'Contact Detail created successfully!',
                'data': serializer.data,
            },
        )

    @authorize_performer_data
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'Contact Detail updated successfully!',
            },
        )

    @authorize_performer_data
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class GalleryViewSet(viewsets.ModelViewSet):
    queryset = Gallery.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = GalleryCreateSerializer

    @get_hita_member_from_request
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance: Gallery = serializer.save()
        if instance.is_profile_picture:
            instance.performer.get_gallery(request.user).exclude(id=instance.id).update(
                is_profile_picture=False
            )
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                'status': 'SUCCESS',
                'message': 'Image uploaded successfully!',
            },
        )

    @get_hita_member_from_request
    def list(self, request, performer, *args, **kwargs):
        gallery = performer.get_gallery(request.user).all()
        serializer = GalleryViewSerializer(gallery, many=True)
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'Gallery retrieved successfully!',
                'data': serializer.data,
            },
        )

    @authorize_performer_data
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        instance: Gallery = self.get_object()
        if instance.is_profile_picture:
            instance.performer.get_gallery(request.user).exclude(id=instance.id).update(
                is_profile_picture=False
            )
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'Gallery updated successfully!',
            },
        )

    @authorize_performer_data
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ShowReelViewSet(viewsets.ModelViewSet):
    queryset = ShowReel.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = ShowReelCreateSerializer

    @get_hita_member_from_request
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                'status': 'SUCCESS',
                'message': 'ShowReel uploaded successfully!',
            },
        )

    @get_hita_member_from_request
    def list(self, request, performer, *args, **kwargs):
        show_reel = performer.show_reel.all()
        serializer = ShowReelViewSerializer(show_reel, many=True)
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'ShowReel retrieved successfully!',
                'data': serializer.data,
            },
        )

    def update(self, request, *args, **kwargs):
        return Response(
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
            data={
                'status': 'FAILED',
                'message': 'Not Allowed!',
            },
        )

    @action(detail=False, methods=['delete'], url_path='delete')
    @get_hita_member_from_request
    def delete_show_reel(self, request, performer, *args, **kwargs):
        performer.show_reel.delete()
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'ShowReel deleted successfully!',
            },
        )

    @action(detail=True, methods=['get'], url_path='stream')
    def stream_video(self, request, *args, **kwargs):
        show_reel = self.get_show_reel()
        file_name = show_reel.file.name
        s3_object = get_s3_object(file_name)

        def file_iterator():
            chunk_size = 8192
            file_obj = s3_object['Body']
            while chunk := file_obj.read(chunk_size):
                yield chunk

        response = StreamingHttpResponse(file_iterator(), content_type='video/mp4')
        response['Content-Disposition'] = (
            f'inline; filename="{os.path.basename(file_name)}"'
        )

        return response

    def get_show_reel(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {'performer__hita_member__user__username': self.kwargs[lookup_url_kwarg]}
        obj = queryset.filter(**filter_kwargs).first()
        if not obj:
            raise ResourceNotFound(
                f'HITAMember profile with username: {self.kwargs[lookup_url_kwarg]} does not exist'
            )
        self.check_object_permissions(self.request, obj)
        return obj
class DepartmentViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in Department.choices]
        return Response(
            data={'status': 'SUCCESS', 'data': queryset}, status=status.HTTP_200_OK
        )


class StudyTypeViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in StudyType.choices]
        return Response(
            data={'status': 'SUCCESS', 'data': queryset}, status=status.HTTP_200_OK
        )


class ContactTypeViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in ContactType.choices]
        return Response(
            data={'status': 'SUCCESS', 'data': queryset}, status=status.HTTP_200_OK
        )


class SkillsViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        data = list(TheaterRole.objects.values_list('name', flat=True))
        return Response(
            data={'status': 'SUCCESS', 'data': data}, status=status.HTTP_200_OK
        )


class HITALocationViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in Location.choices]
        return Response(
            data={'status': 'SUCCESS', 'data': queryset}, status=status.HTTP_200_OK
        )


class HitaMemberViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    model = HITAMember
    queryset = HITAMember.objects.all().order_by('first_name', 'last_name')
    serializer_class = HITAMemberViewSerializer

    def get_permissions(self):
        if self.action in ['create', 'member_status', 'retrieve_member']:
            return [IsAuthenticated()]
        return [IsHITAMemberPermission()]

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {'user': self.request.user}
        obj = queryset.filter(**filter_kwargs).first()
        if not obj:
            raise ResourceNotFound(
                f'HITAMember profile with username: {self.kwargs[lookup_url_kwarg]} does not exist'
            )
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=False, methods=['GET'], url_path='me')
    def retrieve_member(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {
                    'status': 'SUCCESS',
                    'data': serializer.data,
                }
            )
        except ResourceNotFound:
            return Response(
                {
                    'status': 'FAILED',
                    'message': 'No Member Found',
                }
            )

    def create(self, request, *args, **kwargs):

        serializer = HITAMemberCreateSerializer(
            data=request.data, context={'request': request}
        )
        if not serializer.is_valid():
            print(serializer.errors, flush=True)
            print(serializer.error_messages, flush=True)
            return Response(
                {'status': 'FAILED', 'data': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        member = serializer.save()
        return Response(
            {'status': 'SUCCESS', 'data': HITAMemberViewSerializer(member).data},
            status=status.HTTP_201_CREATED,
        )

    @action(methods=['GET'], detail=False, url_path='status')
    def member_status(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=request.user).last()
        if not hita_member:
            return Response(
                data={'status': 'SUCCESS', 'data': {'status': 'NOT_REGISTERED'}},
                status=status.HTTP_200_OK,
            )
        return Response(
            data={
                'status': 'SUCCESS',
                'data': {
                    'status': hita_member.request_status,
                    'performer': hita_member.has_performer,
                    'username': hita_member.user.username,
                },
            },
            status=status.HTTP_200_OK,
        )
