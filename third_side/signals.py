from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from third_side.models import (
    Article,
    Certificate,
    Comment,
    FestivalPost,
    LabProgram,
    LabRegistration,
    Rating,
    Report,
)
from third_side.models.Article import ArticleStatus
from third_side.services.notify import enqueue


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


# ---- notifications (the work itself runs in third_side.tasks)


@receiver(post_save, sender=Report, dispatch_uid='notify_report')
def notify_on_report(sender, instance, created, update_fields=None, **kwargs):
    from third_side import tasks

    if created:
        enqueue(tasks.notify_content_reported, instance.pk)
    elif update_fields and 'reviewed_at' in update_fields and instance.reviewed_at:
        enqueue(tasks.notify_report_reviewed, instance.pk)


@receiver(post_save, sender=Comment, dispatch_uid='notify_comment')
def notify_on_comment(sender, instance, created, **kwargs):
    from third_side import tasks

    if created:
        enqueue(tasks.notify_comment, instance.pk)


@receiver(post_save, sender=Rating, dispatch_uid='notify_rating')
def notify_on_rating(sender, instance, created, **kwargs):
    from third_side import tasks

    if created:
        enqueue(tasks.notify_rating, instance.pk)


@receiver(post_save, sender=FestivalPost, dispatch_uid='notify_festival_post')
def notify_on_festival_post(sender, instance, created, **kwargs):
    from third_side import tasks

    if created:
        enqueue(tasks.notify_festival_post, instance.pk)


@receiver(post_save, sender=LabProgram, dispatch_uid='lab_program_saved')
def on_lab_program_saved(sender, instance, created, **kwargs):
    from third_side import tasks
    from third_side.services.certificates import issue_waiting_english

    if instance.is_published:
        enqueue(tasks.notify_lab_program, instance.pk)
    # English certificates held until the program had English text.
    issue_waiting_english(instance)


@receiver(pre_save, sender=LabRegistration, dispatch_uid='lab_reg_remember_status')
def remember_registration_status(sender, instance, **kwargs):
    instance._old_status = (
        LabRegistration.objects.filter(pk=instance.pk)
        .values_list('status', flat=True)
        .first()
        if instance.pk
        else None
    )


@receiver(post_save, sender=LabRegistration, dispatch_uid='notify_lab_registration')
def notify_on_registration(sender, instance, created, **kwargs):
    from third_side import tasks

    old = getattr(instance, '_old_status', None)
    # The reader's own moves (registering, cancelling) need no telling.
    if created or instance.status == old or instance.status in ('cancelled', 'pending'):
        return
    enqueue(tasks.notify_lab_registration, instance.pk, instance.status)


@receiver(post_save, sender=Certificate, dispatch_uid='notify_certificate')
def notify_on_certificate(sender, instance, created, **kwargs):
    from third_side import tasks

    if created:
        enqueue(tasks.notify_certificate, instance.pk)


@receiver(pre_save, sender=Article, dispatch_uid='article_remember_status')
def remember_article_status(sender, instance, **kwargs):
    instance._old_status = (
        Article.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
        if instance.pk
        else None
    )


@receiver(post_save, sender=Article, dispatch_uid='notify_article_status')
def notify_on_article_status(sender, instance, created, **kwargs):
    from django.utils import timezone

    from third_side import tasks

    old = getattr(instance, '_old_status', None)
    if instance.status == old:
        return
    if not created:
        # Fixed now, so a retried task cannot send the same move twice.
        key = (
            f'status:{instance.pk}:{instance.status}:{int(timezone.now().timestamp())}'
        )
        enqueue(tasks.notify_article_status, instance.pk, instance.status, key)
    if instance.status == ArticleStatus.PUBLISHED:
        enqueue(tasks.notify_article_published, instance.pk)
