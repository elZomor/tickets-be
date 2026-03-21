from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('global_festival', '0002_reservation_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='seat_number',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddConstraint(
            model_name='reservation',
            constraint=models.UniqueConstraint(
                condition=Q(seat_number__isnull=False),
                fields=['show', 'seat_number'],
                name='unique_seat_per_show',
            ),
        ),
    ]
