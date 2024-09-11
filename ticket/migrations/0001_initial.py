# Generated by Django 5.1.1 on 2024-09-11 00:28

import django.db.models.deletion
import utils.json_utils
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Performance',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'name',
                    models.JSONField(default=utils.json_utils.default_localized_model),
                ),
                ('link', models.URLField()),
                ('time', models.DateTimeField()),
                ('initial_reserved_seats', models.IntegerField(default=0)),
                ('reserved_seats', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Theater',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'name',
                    models.JSONField(default=utils.json_utils.default_localized_model),
                ),
                ('capacity', models.IntegerField(default=0)),
                ('location', models.URLField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Reservation',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('name', models.CharField(max_length=255)),
                ('email', models.EmailField(max_length=254)),
                ('reservation_hash', models.CharField(max_length=100, null=True)),
                ('link_delivered', models.BooleanField(default=False)),
                ('guest_arrived', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'performance',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to='ticket.performance',
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name='performance',
            name='theater',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING, to='ticket.theater'
            ),
        ),
    ]
