from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('show', '0006_remove_show_theater_remove_show_time_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='showdate',
            index=models.Index(
                fields=['show', 'date', 'time'], name='showdate_show_date_time_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='showdate',
            index=models.Index(
                fields=['date', 'time'], name='showdate_date_time_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='showdate',
            index=models.Index(
                fields=['theater', 'date', 'time'],
                name='showdate_theater_date_time_idx',
            ),
        ),
    ]
