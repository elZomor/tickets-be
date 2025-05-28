from django.db import models

class ShowDate(models.Model):
    date = models.DateField()
    time = models.TimeField()
    show = models.ForeignKey('show.Show', on_delete=models.CASCADE, related_name='dates')
    theater = models.ForeignKey(to='show.Theater', on_delete=models.DO_NOTHING, related_name='theater_dates')

    def __str__(self):
        return f'{self.show.name}: {self.date} - {self.time}'