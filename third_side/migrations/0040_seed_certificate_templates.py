from pathlib import Path

from django.db import migrations

FILES = Path(__file__).resolve().parent.parent / 'templates' / 'third_side' / 'certificates'
SEED = (('حضور', 'ar', 'attendance_ar.html'), ('Attendance', 'en', 'attendance_en.html'))


def seed(apps, schema_editor):
    Template = apps.get_model('third_side', 'CertificateTemplate')
    for name, language, filename in SEED:
        if Template.objects.filter(language=language).exists():
            continue
        Template.objects.create(
            name=name,
            language=language,
            html=(FILES / filename).read_text(encoding='utf-8'),
            is_default=True,
        )


class Migration(migrations.Migration):
    dependencies = [('third_side', '0039_lab')]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
