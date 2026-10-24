import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('third_side', '0031_email_verification_profile'),
    ]

    operations = [
        migrations.RenameField(model_name='report', old_name='reason', new_name='note'),
        migrations.AddField(
            model_name='report',
            name='reason',
            field=models.CharField(
                blank=True,
                choices=[
                    ('spam', 'Spam'),
                    ('abuse_hate', 'Abuse or hate'),
                    ('misinformation', 'Misinformation'),
                    ('copyright', 'Copyright'),
                    ('other', 'Other'),
                ],
                default='',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='ModerationAction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                (
                    'action',
                    models.CharField(
                        choices=[
                            ('dismiss', 'Dismiss'),
                            ('hide', 'Hide'),
                            ('warn', 'Warn'),
                            ('delete', 'Delete'),
                            ('suspend', 'Suspend'),
                        ],
                        max_length=10,
                    ),
                ),
                ('note', models.TextField(blank=True, default='')),
                ('email_sent', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'author',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='moderation_actions',
                        to='third_side.thirdsideuser',
                    ),
                ),
                (
                    'content_type',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to='contenttypes.contenttype',
                    ),
                ),
                (
                    'moderator',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='third_side_moderation_done',
                        to='third_side.thirdsideuser',
                    ),
                ),
                (
                    'report',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='actions',
                        to='third_side.report',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at', '-id'],
                'permissions': [('suspend_user', 'Can suspend users from moderation')],
            },
        ),
    ]
