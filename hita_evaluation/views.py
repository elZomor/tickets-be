import uuid

from rest_framework import viewsets
from rest_framework.decorators import action

from django.utils import timezone

from hita_evaluation.models import (
    Course,
    CourseProfessor,
    Department,
    Regulation,
    Semester,
    SessionStatus,
    SurveySession,
    SurveyQuestion,
    SurveyAnswer,
    Professor,
    Subject,
    QuestionCategory,
    QuestionType,
)
from hita_evaluation.serializers import (
    CourseListSerializer,
    RegulationSerializer,
    StartSessionRequestSerializer,
    QuestionSerializer,
    SubmitAnswersRequestSerializer,
    DashboardDepartmentSerializer,
    DashboardCourseSerializer,
    DashboardProfessorSerializer,
    DashboardCategorySerializer,
    EvaluationAnswerSerializer,
)
from hita_evaluation.permissions import CanViewDashboardPermission
from utils.Response import get_successful_response, get_bad_request_response


class DepartmentViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = sorted(
            (
                {'value': value, 'label': label}
                for value, label in Department.choices
                if value != Department.GENERAL
            ),
            key=lambda item: item['label'],
        )
        return get_successful_response(data=queryset)


class RegulationViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Regulation.objects.all().order_by('-is_latest', 'name')
    serializer_class = RegulationSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return get_successful_response(data=serializer.data)


class CourseViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = (
        Course.objects.select_related('subject', 'regulations')
        .prefetch_related('professor')
        .order_by('subject__name', 'id')
    )
    serializer_class = CourseListSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Filter by department
        department = request.query_params.get('department')
        if department:
            queryset = queryset.filter(subject__department=department)

        # Filter by regulation
        regulation_id = request.query_params.get('regulation_id')
        if regulation_id:
            queryset = queryset.filter(regulations_id=regulation_id)

        # Filter by is_parallel
        is_parallel = request.query_params.get('is_parallel')
        if is_parallel is not None:
            is_parallel_bool = is_parallel.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_parallel=is_parallel_bool)

        serializer = self.get_serializer(queryset, many=True)
        return get_successful_response(data=serializer.data)


class SurveySessionViewSet(
    viewsets.mixins.CreateModelMixin,
    viewsets.mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = SurveySession.objects.all()
    lookup_field = 'session_id'

    def _build_courses_data(self, courses):
        """Build response data for courses with professors and questions."""
        # Build lookup dict for CourseProfessor grades
        course_ids = [course.id for course in courses]
        course_professor_grades = {}
        for cp in CourseProfessor.objects.filter(course_id__in=course_ids):
            course_professor_grades[(cp.course_id, cp.professor_id)] = cp.get_grade_display()

        courses_data = []
        for course in courses:
            questions = []
            if course.survey_template:
                questions = SurveyQuestion.objects.filter(
                    template=course.survey_template
                )

            questions_data = QuestionSerializer(questions, many=True).data

            professors_data = []
            for professor in course.professor.all().order_by('full_name'):
                # Get grade from CourseProfessor, fallback to Professor's grade
                grade = course_professor_grades.get(
                    (course.id, professor.id),
                    professor.get_grade_display()
                )
                professor_name = f"{grade} {professor.full_name}".strip()

                professors_data.append(
                    {
                        'professor_id': professor.id,
                        'professor_name': professor_name,
                        'questions': questions_data,
                    }
                )

            courses_data.append(
                {
                    'course_id': course.id,
                    'subject_name': course.subject.name,
                    'professors': professors_data,
                }
            )

        courses_data.sort(key=lambda c: (c['subject_name'] or '', c['course_id']))
        return courses_data

    def retrieve(self, request, session_id=None):
        """Resume a draft session by session_id."""
        try:
            session = SurveySession.objects.get(session_id=session_id)
        except SurveySession.DoesNotExist:
            return get_bad_request_response(message='Session not found')

        if session.status == SessionStatus.COMPLETED:
            return get_successful_response(
                data={'status': 'completed'},
                message='This session has been submitted successfully',
            )

        courses = (
            session.courses.select_related('subject', 'regulations')
            .prefetch_related('professor', 'survey_template')
            .order_by('subject__name', 'id')
        )

        courses_data = self._build_courses_data(courses)

        # Fetch saved answers for this session
        saved_answers = SurveyAnswer.objects.filter(
            survey_session=session
        ).select_related('question')

        # Build answers map: {course_id-professor_id: {question_id: answer_data}}
        answers_map = {}
        for answer in saved_answers:
            key = f"{answer.course_id}-{answer.professor_id}"
            if key not in answers_map:
                answers_map[key] = {}

            answer_data = {'question_id': answer.question_id}
            if answer.yes_no_answer is not None:
                answer_data['yes_no_value'] = answer.yes_no_answer
            if answer.rating_answer is not None:
                answer_data['rating_value'] = answer.rating_answer
            if answer.text_answer:
                answer_data['text_value'] = answer.text_answer

            answers_map[key][answer.question_id] = answer_data

        response_data = {
            'session_id': session.session_id,
            'status': session.status,
            'department': session.department,
            'regulation_id': session.regulation_id,
            'is_parallel': session.is_parallel,
            'courses': courses_data,
            'saved_answers': answers_map,
        }

        return get_successful_response(data=response_data)

    def create(self, request, *args, **kwargs):
        serializer = StartSessionRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return get_bad_request_response(
                data=serializer.errors, message='Invalid request data'
            )

        course_ids = serializer.validated_data['course_ids']
        department = serializer.validated_data['department']
        regulation_id = serializer.validated_data['regulation_id']
        is_parallel = serializer.validated_data.get('is_parallel', False)

        # Validate courses exist and match criteria
        courses = (
            Course.objects.filter(
                id__in=course_ids,
                subject__department=department,
                regulations_id=regulation_id,
                is_parallel=is_parallel,
            )
            .select_related('subject', 'regulations')
            .prefetch_related('professor', 'survey_template')
            .order_by('subject__name', 'id')
        )
        if courses.count() != len(course_ids):
            return get_bad_request_response(
                message='One or more courses not found or do not match the selected criteria'
            )

        # Create draft session
        session_id = uuid.uuid4()
        session = SurveySession.objects.create(
            session_id=session_id,
            department=department,
            regulation_id=regulation_id,
            is_parallel=is_parallel,
        )
        session.courses.set(courses)

        courses_data = self._build_courses_data(courses)
        response_data = {'session_id': session_id, 'courses': courses_data}

        return get_successful_response(data=response_data)

    @action(detail=False, methods=['post'], url_path='submit')
    def submit_answers(self, request):
        serializer = SubmitAnswersRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return get_bad_request_response(
                data=serializer.errors, message='Invalid request data'
            )

        session_id = serializer.validated_data['session_id']
        courses_data = serializer.validated_data['courses']

        # Validate session exists and is not already completed
        try:
            session = SurveySession.objects.get(session_id=session_id)
        except SurveySession.DoesNotExist:
            return get_bad_request_response(message='Session not found')

        if session.status == SessionStatus.COMPLETED:
            return get_bad_request_response(message='Session already submitted')

        # Create SurveyAnswer records
        answers_to_create = []
        for course_data in courses_data:
            course_id = course_data['course_id']

            try:
                course = Course.objects.get(id=course_id)
            except Course.DoesNotExist:
                return get_bad_request_response(message=f'Course {course_id} not found')

            for professor_data in course_data['professors']:
                professor_id = professor_data['professor_id']

                try:
                    professor = Professor.objects.get(id=professor_id)
                except Professor.DoesNotExist:
                    return get_bad_request_response(
                        message=f'Professor {professor_id} not found'
                    )

                for answer_data in professor_data['answers']:
                    question_id = answer_data['question_id']

                    try:
                        question = SurveyQuestion.objects.get(id=question_id)
                    except SurveyQuestion.DoesNotExist:
                        return get_bad_request_response(
                            message=f'Question {question_id} not found'
                        )

                    answer = SurveyAnswer(
                        survey_session=session,
                        course=course,
                        professor=professor,
                        question=question,
                        yes_no_answer=answer_data.get('yes_no_value'),
                        rating_answer=answer_data.get('rating_value'),
                        text_answer=answer_data.get('text_value'),
                    )
                    answers_to_create.append(answer)

        # Bulk create all answers
        SurveyAnswer.objects.bulk_create(answers_to_create)

        # Mark session as completed
        session.status = SessionStatus.COMPLETED
        session.submitted_at = timezone.now()
        session.save(update_fields=['status', 'submitted_at'])

        return get_successful_response(
            data={'answers_count': len(answers_to_create)},
            message='Answers submitted successfully',
        )

    @action(detail=False, methods=['post'], url_path='save')
    def save_answers(self, request):
        """Save answers without completing the session (for resuming later)."""
        serializer = SubmitAnswersRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return get_bad_request_response(
                data=serializer.errors, message='Invalid request data'
            )

        session_id = serializer.validated_data['session_id']
        courses_data = serializer.validated_data['courses']

        # Validate session exists and is not already completed
        try:
            session = SurveySession.objects.get(session_id=session_id)
        except SurveySession.DoesNotExist:
            return get_bad_request_response(message='Session not found')

        if session.status == SessionStatus.COMPLETED:
            return get_bad_request_response(message='Session already submitted')

        # Delete existing answers for this session (to handle updates)
        SurveyAnswer.objects.filter(survey_session=session).delete()

        # Create SurveyAnswer records
        answers_to_create = []
        for course_data in courses_data:
            course_id = course_data['course_id']

            try:
                course = Course.objects.get(id=course_id)
            except Course.DoesNotExist:
                return get_bad_request_response(message=f'Course {course_id} not found')

            for professor_data in course_data['professors']:
                professor_id = professor_data['professor_id']

                try:
                    professor = Professor.objects.get(id=professor_id)
                except Professor.DoesNotExist:
                    return get_bad_request_response(
                        message=f'Professor {professor_id} not found'
                    )

                for answer_data in professor_data['answers']:
                    question_id = answer_data['question_id']

                    # Skip empty answers
                    if (
                        answer_data.get('yes_no_value') is None
                        and answer_data.get('rating_value') is None
                        and not answer_data.get('text_value')
                    ):
                        continue

                    try:
                        question = SurveyQuestion.objects.get(id=question_id)
                    except SurveyQuestion.DoesNotExist:
                        return get_bad_request_response(
                            message=f'Question {question_id} not found'
                        )

                    answer = SurveyAnswer(
                        survey_session=session,
                        course=course,
                        professor=professor,
                        question=question,
                        yes_no_answer=answer_data.get('yes_no_value'),
                        rating_answer=answer_data.get('rating_value'),
                        text_answer=answer_data.get('text_value'),
                    )
                    answers_to_create.append(answer)

        # Bulk create all answers
        SurveyAnswer.objects.bulk_create(answers_to_create)

        # Update session status to IN_PROGRESS if there are answers
        if len(answers_to_create) > 0:
            session.status = SessionStatus.IN_PROGRESS
            session.save(update_fields=['status'])

        return get_successful_response(
            data={'answers_count': len(answers_to_create)},
            message='Answers saved successfully',
        )


class DashboardViewSet(viewsets.GenericViewSet):
    """ViewSet for dashboard analytics endpoints."""

    permission_classes = [CanViewDashboardPermission]

    @action(detail=False, methods=['get'], url_path='semesters')
    def semesters(self, request):
        """Get semesters for dashboard filters."""
        queryset = Semester.objects.all().order_by('-year', '-type')

        data = [
            {
                'id': str(semester.id),
                'year': semester.year,
                'type': semester.type,
                'type_display': semester.get_type_display(),
                'is_current': semester.is_current,
            }
            for semester in queryset
        ]

        return get_successful_response(data=data)

    @action(detail=False, methods=['get'], url_path='answers')
    def answers(self, request):
        """Get evaluation answers with ratings for dashboard visualizations."""
        queryset = SurveyAnswer.objects.filter(
            rating_answer__isnull=False,
            survey_session__status=SessionStatus.COMPLETED,
        ).select_related(
            'survey_session',
            'survey_session__regulation',
            'course',
            'course__subject',
            'course__semester',
            'professor',
            'question',
            'question__question_category',
        )

        # Filter by semester IDs
        semester_ids = request.query_params.getlist('semester_ids')
        if semester_ids:
            queryset = queryset.filter(course__semester_id__in=semester_ids)

        # Filter by department IDs
        department_ids = request.query_params.getlist('department_ids')
        if department_ids:
            queryset = queryset.filter(course__subject__department__in=department_ids)

        # Filter by course IDs
        course_ids = request.query_params.getlist('course_ids')
        if course_ids:
            queryset = queryset.filter(course_id__in=course_ids)

        # Filter by professor IDs
        professor_ids = request.query_params.getlist('professor_ids')
        if professor_ids:
            queryset = queryset.filter(professor_id__in=professor_ids)

        # Filter by regulation IDs
        regulation_ids = request.query_params.getlist('regulation_ids')
        if regulation_ids:
            queryset = queryset.filter(survey_session__regulation_id__in=regulation_ids)

        # Filter by is_parallel
        is_parallel = request.query_params.get('is_parallel')
        if is_parallel is not None:
            is_parallel_bool = is_parallel.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(course__is_parallel=is_parallel_bool)

        # Build lookup dict for CourseProfessor grades
        # Get unique (course_id, professor_id) pairs from the queryset
        course_professor_pairs = queryset.values_list(
            'course_id', 'professor_id'
        ).distinct()

        # Fetch CourseProfessor records for these pairs
        course_professor_grades = {}
        for cp in CourseProfessor.objects.filter(
            course_id__in=[p[0] for p in course_professor_pairs],
            professor_id__in=[p[1] for p in course_professor_pairs],
        ).select_related('professor'):
            course_professor_grades[(cp.course_id, cp.professor_id)] = cp.get_grade_display()

        # Build response data
        data = []
        for answer in queryset:
            department = (
                answer.course.subject.department if answer.course.subject else None
            )
            department_name = Department(department).label if department else ''
            category = answer.question.question_category

            # Get grade from CourseProfessor, fallback to Professor's grade
            grade = course_professor_grades.get(
                (answer.course_id, answer.professor_id),
                answer.professor.get_grade_display() if answer.professor else ''
            )
            professor_name = (
                f"{grade} {answer.professor.full_name}".strip()
                if answer.professor
                else ''
            )

            data.append(
                {
                    'evaluation_id': str(answer.survey_session.session_id),
                    'submitted_at': answer.survey_session.submitted_at,
                    'department_id': department or '',
                    'department_name': department_name,
                    'course_id': str(answer.course_id),
                    'course_name': (
                        answer.course.subject.name if answer.course.subject else ''
                    ),
                    'professor_id': str(answer.professor_id),
                    'professor_name': professor_name,
                    'regulation': (
                        answer.survey_session.regulation.name
                        if answer.survey_session.regulation
                        else None
                    ),
                    'is_parallel': answer.course.is_parallel,
                    'question_id': str(answer.question_id),
                    'question_text': answer.question.question_text,
                    'category_id': str(category.id) if category else '',
                    'category_name': category.name if category else '',
                    'rating': answer.rating_answer,
                }
            )

        return get_successful_response(data=data)

    @action(detail=False, methods=['get'], url_path='departments')
    def departments(self, request):
        """Get departments for dashboard filters."""
        data = [
            {
                'id': value,
                'name_en': label,
                'name_ar': label,
            }
            for value, label in Department.choices
            if value != Department.GENERAL
        ]
        data.sort(key=lambda x: x['name_en'])
        return get_successful_response(data=data)

    @action(detail=False, methods=['get'], url_path='courses')
    def courses(self, request):
        """Get courses for dashboard filters."""
        queryset = Subject.objects.all().order_by('name')

        # Filter by department IDs
        department_ids = request.query_params.getlist('department_ids')
        if department_ids:
            queryset = queryset.filter(department__in=department_ids)

        data = [
            {
                'id': str(subject.id),
                'name_en': subject.name,
                'name_ar': subject.name,
                'department_id': subject.department or '',
            }
            for subject in queryset
        ]

        return get_successful_response(data=data)

    @action(detail=False, methods=['get'], url_path='professors')
    def professors(self, request):
        """Get professors for dashboard filters."""
        queryset = Professor.objects.all().order_by('full_name')

        # Filter by department IDs
        department_ids = request.query_params.getlist('department_ids')
        if department_ids:
            queryset = queryset.filter(department__in=department_ids)

        data = [
            {
                'id': str(professor.id),
                'name_en': professor.get_grade_display() + ' ' + professor.full_name,
                'name_ar': professor.get_grade_display() + ' ' + professor.full_name,
                'department_id': professor.department or '',
            }
            for professor in queryset
        ]

        return get_successful_response(data=data)

    @action(detail=False, methods=['get'], url_path='categories')
    def categories(self, request):
        """Get question categories for dashboard."""
        queryset = QuestionCategory.objects.all().order_by('id')

        data = [
            {
                'id': str(category.id),
                'name_en': category.name,
                'name_ar': category.name,
                'order_index': category.id,
            }
            for category in queryset
        ]

        return get_successful_response(data=data)

    @action(detail=False, methods=['get'], url_path='regulations')
    def regulations(self, request):
        """Get regulations for dashboard filters."""
        queryset = Regulation.objects.all().order_by('-is_latest', 'name')

        data = [
            {
                'id': str(regulation.id),
                'name': regulation.name,
                'is_latest': regulation.is_latest,
            }
            for regulation in queryset
        ]

        return get_successful_response(data=data)
