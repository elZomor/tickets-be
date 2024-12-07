from django.db import models


class ContactType(models.TextChoices):
    MOBILE = 'MOBILE', 'Mobile'
    WHATSAPP = 'WHATSAPP', 'WhatsApp'
    FACEBOOK = 'FACEBOOK', 'Facebook'
    INSTAGRAM = 'INSTAGRAM', 'Instagram'
    TIK_TOK = 'TIK_TOK', 'TikTok'
    YOUTUBE = 'YOUTUBE', 'YouTube'
    TWITTER = 'TWITTER', 'Twitter'
    SHOWREEL = 'SHOWREEL', 'ShowReel'
    VIMEO = 'VIMEO', 'Vimeo'
    BEHANCE = 'BEHANCE', 'Behance'
    GOOGLE_DRIVE = 'GOOGLE_DRIVE', 'Google Drive'
    TELEGRAM = 'TELEGRAM', 'Telegram'
    SOUND_CLOUD = 'SOUND_CLOUD' , 'SoundCloud'
    OTHER = 'OTHER', 'Other'


class ContactDetail(models.Model):
    performer = models.ForeignKey(
        'hita.Performer', on_delete=models.CASCADE, related_name='contact_detail_list'
    )
    contact_type = models.CharField(
        max_length=20,
        choices=ContactType.choices,
        default=ContactType.MOBILE.value,
    )
    contact_info = models.CharField(max_length=100)

    class Meta:
        ordering = ('contact_type',)
