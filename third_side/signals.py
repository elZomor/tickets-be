from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from third_side.models import Article, Comment, Report


@receiver(post_save, sender=Report)
def auto_hide_on_report_threshold(sender, instance, created, **kwargs):
    if not created:
        return

    report_count = Report.objects.filter(
        content_type=instance.content_type, object_id=instance.object_id
    ).count()

    if report_count < settings.REPORT_AUTO_HIDE_THRESHOLD:
        return

    target = instance.target
    if isinstance(target, (Article, Comment)) and not target.is_hidden:
        target.is_hidden = True
        target.save(update_fields=['is_hidden'])
