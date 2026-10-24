from django.db import migrations


def editors_to_superusers(apps, schema_editor):
    """Every editor keeps full access; narrow them to a Group afterwards."""
    user = apps.get_model('third_side', 'ThirdSideUser')
    user.objects.filter(role='EDITOR').update(is_superuser=True)


def superusers_to_editors(apps, schema_editor):
    user = apps.get_model('third_side', 'ThirdSideUser')
    user.objects.filter(is_superuser=True).update(role='EDITOR')


class Migration(migrations.Migration):

    dependencies = [
        ('third_side', '0028_staff_permissions'),
    ]

    operations = [
        migrations.RunPython(editors_to_superusers, superusers_to_editors),
    ]
