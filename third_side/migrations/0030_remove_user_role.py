from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('third_side', '0029_editors_to_superusers'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='thirdsideuser',
            name='role',
        ),
    ]
