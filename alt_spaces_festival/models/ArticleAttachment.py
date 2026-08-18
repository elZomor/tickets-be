from django.db import models

from alt_spaces_festival.models.Article import Article
from utils.code_utils import upload_to_alt_spaces_festival_article_attachment


class ArticleAttachment(models.Model):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name='article_attachments'
    )
    file = models.FileField(upload_to=upload_to_alt_spaces_festival_article_attachment)
    position = models.IntegerField(default=0)
