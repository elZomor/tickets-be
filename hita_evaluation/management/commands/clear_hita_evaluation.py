from django.core.management.base import BaseCommand
from django.db import transaction

from hita_evaluation import models as m


class Command(BaseCommand):
    help = 'Delete all data that belongs to the hita_evaluation app.'

    def handle(self, *args, **options):
        model_order = [
            m.SurveyAnswer,
            m.SurveySession,
            m.Course,
            m.Semester,
            m.SurveyQuestion,
            m.SurveyTemplate,
            m.QuestionCategory,
            m.Subject,
            m.Professor,
        ]

        with transaction.atomic():
            total_deleted = 0
            for model in model_order:
                count, _ = model.objects.all().delete()
                total_deleted += count
                self.stdout.write(
                    f'{model.__name__}: deleted {count} record{"s" if count != 1 else ""}'
                )

        self.stdout.write(self.style.SUCCESS(f'Done. Total deleted: {total_deleted}'))
