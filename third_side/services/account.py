"""Account deletion (a reader removing their own account).

Personal data goes with the account: the FKs that hold it cascade (comments,
likes, ratings, follows, saved articles, notifications, preferences, push
devices, reports filed, terms acceptances). Content the site keeps survives
without the link: published articles stay under the writer's byline and their
uploads stay (`created_by` / `uploaded_by` become null). Unfinished submissions
nobody else has picked up are deleted with the account.
"""

from django.db import transaction

from third_side.models import Article
from third_side.models.Article import ArticleStatus as S

# Submissions still private to their author: removed with the account. Anything
# further along (editing, scheduled, published, archived) is editorial content.
PRIVATE_STATUSES = [
    S.DRAFT,
    S.SUBMITTED,
    S.UNDER_REVIEW,
    S.CHANGES_REQUESTED,
    S.REJECTED,
]


def is_staff_account(user):
    """Staff (any role) are removed by an administrator, not through the API."""
    return user.is_superuser or user.groups.exists()


def delete_account(user):
    avatar = user.avatar
    name, storage = avatar.name, avatar.storage
    with transaction.atomic():
        Article.objects.filter(
            created_by=user, via_website=True, status__in=PRIVATE_STATUSES
        ).delete()
        user.delete()
        if name:
            transaction.on_commit(lambda: storage.delete(name))
