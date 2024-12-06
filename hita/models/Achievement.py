from django.db import models


class Achievement(models.Model):
    performer = models.ForeignKey(
        'hita.Performer', on_delete=models.CASCADE, related_name='achievements'
    )
    position = models.CharField(max_length=100)
    field = models.CharField(max_length=100)
    show_name = models.CharField(max_length=100)
    festival_name = models.CharField(max_length=100)
    year = models.IntegerField()

    class Meta:
        ordering = ['-year']
