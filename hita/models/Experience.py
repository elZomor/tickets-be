from django.db import models


class TheaterRolesChoices(models.TextChoices):
    # ACTING = 'ACTING', 'Acting'
    ACTOR = 'ACTOR', 'Actor/Actress'  # To be removed
    # WRITING = 'WRITING', 'Writing'
    AUTHOR = 'AUTHOR', 'Author'  # To be removed
    TREATMENT = 'TREATMENT', 'Treatment'
    # DIRECTING = 'DIRECTING', 'Directing'
    DIRECTOR = 'DIRECTOR', 'Director'  # To be removed
    DIRECTING_CAST = 'DIRECTING_CAST', 'Directing Cast'
    # DECOR_DESIGN = 'DECOR_DESIGN', 'Decor Design'
    # DECOR_IMPLEMENTATION = 'DECOR_IMPLEMENTATION', 'Decor Implementation'
    DECOR = 'DECOR', 'Decor'  # To be removed
    STYLING = 'STYLING', 'Styling'
    MAKEUP = 'MAKEUP', 'Makeup'
    # LIGHTING_DESIGN = 'LIGHTING_DESIGN', 'Lighting Design'
    # LIGHTING_IMPLEMENTATION = 'LIGHTING_IMPLEMENTATION', 'Lighting Implementation'
    LIGHTING = 'LIGHTING', 'Lighting'  # To be removed
    # COMPOSING_MUSIC = 'COMPOSING_MUSIC', 'Composing Music'
    # COMPOSING_SONGS = 'COMPOSING_SONGS', 'Composing Songs'
    COMPOSING = 'COMPOSING', 'Composing'  # To be removed
    MUSIC_ARRANGEMENT = 'MUSIC_ARRANGEMENT', 'Music Arrangement'
    # MUSIC_PREPARATION = 'MUSIC_PREPARATION', 'Music Preparation'
    # MUSIC_IMPLEMENTATION = 'MUSIC_IMPLEMENTATION', 'Music Implementation'
    MUSICIAN = 'MUSICIAN', 'Musician'
    CHOREOGRAPHY = 'CHOREOGRAPHY', 'Choreography'
    # DANCING = 'DANCING', 'Dancing'
    DANCER = 'DANCER', 'Dancer'  # To be removed
    SINGING = 'SINGING', 'Singing'
    VIDEOGRAPHY = 'VIDEOGRAPHY', 'Videography'
    PHOTOGRAPHY = 'PHOTOGRAPHY', 'Photography'
    VIDEO_MAPPING = 'VIDEO_MAPPING', 'Video Mapping'
    GRAPHICS_DESIGNER = 'GRAPHICS_DESIGNER', 'Graphics Designer'
    HAIR_DRESSER = 'HAIR_DRESSER', 'Hair Dresser'


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
    role_name = models.CharField(max_length=20, null=True, blank=True)
    role_brief = models.CharField(max_length=50, null=True, blank=True)
    producer = models.CharField(max_length=30, null=True, blank=True)
    director = models.CharField(max_length=20)
    venue = models.CharField(max_length=50, null=True, blank=True)
    role = models.ManyToManyField(TheaterRole)
    year = models.IntegerField()
    duration = models.IntegerField(null=True, blank=True)
    show_type = models.CharField(
        max_length=20,
    )
    festival_name = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        ordering = ('-year',)
