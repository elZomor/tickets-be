from django.db import models


class PublicChannelTypes(models.TextChoices):
    FACEBOOK = 'FACEBOOK', 'Facebook'
    INSTAGRAM = 'INSTAGRAM', 'Instagram'
    TIK_TOK = 'TIK_TOK', 'TikTok'
    YOUTUBE = 'YOUTUBE', 'YouTube'
    TWITTER = 'TWITTER', 'Twitter'
    SHOWREEL = 'SHOWREEL', 'ShowReel'
    VIMEO = 'VIMEO', 'Vimeo'
    BEHANCE = 'BEHANCE', 'Behance'
    GOOGLE_DRIVE = 'GOOGLE_DRIVE', 'Google Drive'
    SOUND_CLOUD = 'SOUND_CLOUD', 'SoundCloud'
    OTHER = 'OTHER', 'Other'


class ContactSpecificType(models.TextChoices):
    MOBILE = 'MOBILE', 'Mobile'
    WHATSAPP = 'WHATSAPP', 'WhatsApp'
    TELEGRAM = 'TELEGRAM', 'Telegram'


ContactTypes = ContactSpecificType.choices + PublicChannelTypes.choices
