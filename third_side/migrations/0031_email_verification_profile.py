from django.db import migrations, models

from third_side.models.ThirdSideUser import GENDERS, GOVERNORATES, LANGUAGES


def grandfather_existing(apps, schema_editor):
    """Accounts that predate verification keep working: mark them verified."""
    User = apps.get_model('third_side', 'ThirdSideUser')
    User.objects.update(email_verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ('third_side', '0030_remove_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='thirdsideuser',
            name='email_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='thirdsideuser',
            name='email_verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='thirdsideuser',
            name='language',
            field=models.CharField(choices=LANGUAGES, default='ar', max_length=2),
        ),
        migrations.AddField(
            model_name='thirdsideuser',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='thirdsideuser',
            name='gender',
            field=models.CharField(blank=True, choices=GENDERS, default='', max_length=10),
        ),
        migrations.AddField(
            model_name='thirdsideuser',
            name='governorate',
            field=models.CharField(
                blank=True, choices=GOVERNORATES, default='', max_length=20
            ),
        ),
        migrations.AddField(
            model_name='thirdsideuser',
            name='bio',
            field=models.TextField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='thirdsideuser',
            name='newsletter_opt_in',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(grandfather_existing, migrations.RunPython.noop),
    ]
