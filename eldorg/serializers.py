from rest_framework import serializers

from eldorg.models import Script


class ScriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Script
        fields = [
            'id',
            'author',
            'title',
            'synopsis',
            'file',
            'year',
            'genre',
            'cover'
        ]