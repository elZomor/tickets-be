from django.db import models


class TheaterRolesChoices(models.TextChoices):
    ACTOR = 'ACTOR', 'Actor/Actress'
    AUTHOR = 'AUTHOR', 'Author'
    TREATMENT = 'TREATMENT', 'Treatment'
    DIRECTOR = 'DIRECTOR', 'Director'
    DIRECTING_CAST = 'DIRECTING_CAST', 'Directing Cast'
    DECOR = 'DECOR', 'Decor'
    STYLING = 'STYLING', 'Styling'
    MAKEUP = 'MAKEUP', 'Makeup'
    LIGHTING = 'LIGHTING', 'Lighting'
    COMPOSING = 'COMPOSING', 'Composing'
    MUSIC_ARRANGEMENT = 'MUSIC_ARRANGEMENT', 'Music Arrangement'
    MUSICIAN = 'MUSICIAN', 'Musician'
    CHOREOGRAPHY = 'CHOREOGRAPHY', 'Choreography'
    DANCER = 'DANCER', 'Dancer'


class ShowTypeChoices(models.TextChoices):
    THEATER = 'THEATER', 'Theater'
    TV = 'TV', 'TV'
    MOVIE = 'MOVIE', 'Movie'
    RADIO = 'RADIO', 'Radio'
    DUBBING = 'DUBBING', 'Dubbing'


class TheaterRole(models.Model):
    name = models.CharField(
        max_length=40,
        choices=TheaterRolesChoices.choices,
        default=TheaterRolesChoices.ACTOR.value,
    )

    def __str__(self):
        return self.name


class Experience(models.Model):
    performer = models.ForeignKey(
        'hita.Performer', on_delete=models.CASCADE, related_name='experiences'
    )

    show_name = models.CharField(max_length=100)
    director = models.CharField(max_length=50)
    venue = models.CharField(max_length=50, null=True, blank=True)
    role = models.ManyToManyField(TheaterRole)
    year = models.IntegerField()
    duration = models.IntegerField(null=True, blank=True)
    show_type = models.CharField(
        max_length=20,
    )
