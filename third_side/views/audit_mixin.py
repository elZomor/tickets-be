from django.db import transaction

from third_side.models.ActivityLog import ActivityAction
from third_side.services import audit


class AuditedMixin:
    """Editor writes of a viewset are recorded in the activity log.

    The change and its log row commit together. Put it before the DRF mixins.
    Override `save_new` when a create needs extra `serializer.save()` arguments.
    """

    def save_new(self, serializer):
        serializer.save()

    def perform_create(self, serializer):
        with transaction.atomic():
            self.save_new(serializer)
            instance = serializer.instance
            audit.record(
                self.request,
                ActivityAction.CREATE,
                instance,
                {},
                audit.snapshot(instance),
            )

    def perform_update(self, serializer):
        with transaction.atomic():
            before = audit.snapshot(serializer.instance)
            serializer.save()
            instance = serializer.instance
            audit.record(
                self.request,
                ActivityAction.UPDATE,
                instance,
                before,
                audit.snapshot(instance),
            )

    def perform_destroy(self, instance):
        with transaction.atomic():
            before = audit.snapshot(instance)
            pk, repr_ = instance.pk, audit.object_repr(instance)
            instance.delete()
            audit.record(
                self.request,
                ActivityAction.DELETE,
                instance,
                before,
                {},
                pk=pk,
                repr_=repr_,
            )
