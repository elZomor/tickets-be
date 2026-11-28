"""Lab programs: registration rules and the addresses the frontend serves."""

from django.db import transaction
from django.utils import timezone

from third_side.i18n import LOCALES, localize
from third_side.models import LabProgram, LabRegistration
from third_side.models.LabProgram import RegistrationMode
from third_side.models.LabRegistration import RegistrationStatus

# Keep in step with the FE dictionaries (labPage / certificatePage urlSegment).
LAB_SEGMENT = {'ar': 'مختبر-الضلع', 'en': 'lab'}
CERTIFICATE_SEGMENT = {'ar': 'شهادة', 'en': 'certificate'}
MY_CERTIFICATES_SEGMENT = {'ar': 'شهاداتي', 'en': 'my-certificates'}

# Statuses that hold a seat.
SEATED = (RegistrationStatus.ACCEPTED,)
# Statuses a reader can still cancel or that block a second registration.
LIVE = (
    RegistrationStatus.PENDING,
    RegistrationStatus.ACCEPTED,
    RegistrationStatus.WAITLISTED,
)


class _LabSection:
    """The Lab as a follow target (there is one Lab, id 0)."""

    pk = 0
    slug = 'lab'
    name_i18n = {'ar': 'مختبر الضلع', 'en': 'Third Side Lab'}


LAB_SECTION = _LabSection()


def lab_paths():
    return {lang: f'/{lang}/{LAB_SEGMENT[lang]}' for lang in LOCALES}


def program_paths(program):
    return {
        lang: f'/{lang}/{LAB_SEGMENT[lang]}/'
        f'{localize(program.slug_i18n, lang, program.slug)}'
        for lang in LOCALES
    }


def certificate_paths(code):
    return {lang: f'/{lang}/{CERTIFICATE_SEGMENT[lang]}/{code}' for lang in LOCALES}


def seats_taken(program):
    return program.registrations.filter(status__in=SEATED).count()


def seats_left(program):
    if program.capacity is None:
        return None
    return max(program.capacity - seats_taken(program), 0)


def registration_state(program, now=None):
    """open | full | closed | external | ended, as the program page shows it."""
    now = now or timezone.now()
    mode = program.registration_mode
    if program.ends_on < now.date():
        return 'ended'
    if mode == RegistrationMode.EXTERNAL:
        return 'external' if program.external_url else 'closed'
    if mode == RegistrationMode.CLOSED:
        return 'closed'
    if program.registration_deadline and program.registration_deadline < now:
        return 'closed'
    if mode == RegistrationMode.DIRECT and seats_left(program) == 0:
        # Direct mode still takes names, on the waiting list.
        return 'full'
    return 'open'


class RegistrationError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


@transaction.atomic
def register(program, user, answers):
    """Register `user`, or reopen a cancelled/rejected registration.

    Direct mode seats at once while seats remain, then waitlists; application
    mode always starts pending. Returns the registration.
    """
    program = LabProgram.objects.select_for_update().get(pk=program.pk)
    state = registration_state(program)
    if state not in ('open', 'full'):
        raise RegistrationError(state)
    existing = LabRegistration.objects.filter(program=program, user=user).first()
    if existing and existing.status in LIVE:
        return existing
    if existing and existing.status == RegistrationStatus.REJECTED:
        raise RegistrationError('rejected')
    if program.registration_mode == RegistrationMode.DIRECT:
        left = seats_left(program)
        status = (
            RegistrationStatus.ACCEPTED
            if left is None or left > 0
            else RegistrationStatus.WAITLISTED
        )
    else:
        status = RegistrationStatus.PENDING
    if existing:
        existing.status = status
        existing.answers = answers
        existing.save(update_fields=['status', 'answers', 'updated_at'])
        return existing
    return LabRegistration.objects.create(
        program=program, user=user, status=status, answers=answers
    )


@transaction.atomic
def cancel(registration):
    """The reader gives up their seat; the first waitlisted reader (direct mode)
    takes it."""
    was_seated = registration.status in SEATED
    registration.status = RegistrationStatus.CANCELLED
    registration.save(update_fields=['status', 'updated_at'])
    program = registration.program
    if was_seated and program.registration_mode == RegistrationMode.DIRECT:
        nxt = (
            program.registrations.filter(status=RegistrationStatus.WAITLISTED)
            .order_by('created_at', 'id')
            .first()
        )
        if nxt is not None:
            nxt.status = RegistrationStatus.ACCEPTED
            nxt.save(update_fields=['status', 'updated_at'])
