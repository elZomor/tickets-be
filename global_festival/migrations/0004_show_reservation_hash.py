from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('global_festival', '0003_add_seat_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='show',
            name='reservation_hash',
            field=models.CharField(blank=True, default=None, max_length=64, null=True, unique=True),
        ),
    ]
