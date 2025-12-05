from django.db import models

from hita_arab_festival.models.Article import Article
from utils.code_utils import upload_to_arabic_festival_article_attachment


class ArticleAttachment(models.Model):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name='article_attachments'
    )
    file = models.FileField(upload_to=upload_to_arabic_festival_article_attachment)
    position = models.IntegerField(default=0)
