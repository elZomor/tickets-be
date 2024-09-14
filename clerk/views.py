from django.contrib.auth.models import User
from rest_framework import viewsets, mixins
from rest_framework.response import Response

from clerk.models import EventTypeEnum, ClerkUser, SourceChoices
from clerk.serializer import ClerkSerializer


class ClerkViewSet(viewsets.ViewSet, mixins.CreateModelMixin):

    def create(self, request, *args, **kwargs):
        serializer_data = {
            'body': request.body,
            'svix_id': request.headers.get('svix_id'),
            'svix_timestamp': request.headers.get('svix_timestamp'),
            'svix_signature': request.headers.get('svix_signature'),
        }
        serializer = ClerkSerializer()
        serializer.validate(data=serializer_data)
        data = request.data
        user_data = data.get('data')
        if data.get('type') == EventTypeEnum.USER_CREATED.value:
            primary_mail_data = user_data.get('email_addresses')[0]
            user = User.objects.get_or_create(username=user_data.get('username'),
                                              defaults={
                                                  'email': primary_mail_data.get('email_address'),
                                                  'first_name': user_data.get('first_name'),
                                                  'last_name': user_data.get('last_name')})[0]
            clerk_user = ClerkUser()
            clerk_user.user = user
            clerk_user.clerk_id = user_data.get('id')
            clerk_user.source = primary_mail_data.get('verification').get('strategy')
            clerk_user.save()
            print("user created successfully!")
        return Response({'status': 'success'})
