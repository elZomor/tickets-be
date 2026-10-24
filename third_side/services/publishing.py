from django.utils import timezone

from third_side.models import Article
from third_side.models.Article import ArticleStatus


def promote_due_articles():
    """Publish the scheduled articles whose time has come.

    Saved one by one (not a bulk update) so the signals fire and the author and
    followers are notified. Returns how many were promoted.
    """
    due = Article.objects.filter(
        status=ArticleStatus.SCHEDULED, published_at__lte=timezone.now()
    )
    promoted = 0
    for article in due:
        article.status = ArticleStatus.PUBLISHED
        article.save(update_fields=['status', 'updated_at'])
        promoted += 1
    return promoted
