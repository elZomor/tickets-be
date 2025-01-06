from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework import serializers


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        identifier = attrs.get("username")
        password = attrs.get("password")
        if identifier.__contains__('@'):
            user = User.objects.filter(email=identifier).last()
            if not user or not user.check_password(password):
                raise serializers.ValidationError("Invalid credentials")
        else:
            user = authenticate(
                request=self.context['request'], username=identifier, password=password
            )
        if user is None:
            raise serializers.ValidationError("Invalid credentials")
        attrs["username"] = user.username

        if not user.is_active:
            return True

        return super().validate(attrs)
