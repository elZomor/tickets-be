from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('global_festival', '0004_show_reservation_hash'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='reservation',
            constraint=models.UniqueConstraint(
                condition=Q(user__isnull=False),
                fields=['user', 'show'],
                name='unique_user_reservation_per_show',
            ),
        ),
    ]
