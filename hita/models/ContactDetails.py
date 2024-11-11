from django.db import models


class ContactTypeChoices(models.TextChoices):
    MOBILE = 'MOBILE', 'Mobile'
    WHATSAPP = 'WHATSAPP', 'WhatsApp'
    FACEBOOK = 'FACEBOOK', 'Facebook'
    INSTAGRAM = 'INSTAGRAM', 'Instagram'
    TIK_TOK = 'TIK_TOK', 'TikTok'
    YOUTUBE = 'YOUTUBE', 'YouTube'
    TWITTER = 'TWITTER', 'Twitter'
    OTHER = 'OTHER', 'Other'


class ContactDetails(models.Model):
    performer = models.ForeignKey('hita.Performer', on_delete=models.CASCADE,
                                        related_name='contact_details_list')
    contact_type = models.CharField(max_length=20, choices=ContactTypeChoices.choices,
                                    default=ContactTypeChoices.MOBILE.value)
    contact_info = models.CharField(max_length=100)
