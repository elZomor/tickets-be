import uuid

from rest_framework import viewsets
from rest_framework.decorators import action

from hita_evaluation.models import (
    Course,
    Department,
    SurveySession,
    SurveyQuestion,
    SurveyAnswer,
    Professor,
)
from hita_evaluation.serializers import (
    CourseListSerializer,
    StartSessionRequestSerializer,
    QuestionSerializer,
    SubmitAnswersRequestSerializer,
)
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


class CourseViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = (
        Course.objects.select_related('subject')
        .prefetch_related('professor')
        .order_by('subject__name', 'id')
    )
    serializer_class = CourseListSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return get_successful_response(data=serializer.data)


class SurveySessionViewSet(viewsets.mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = SurveySession.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = StartSessionRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return get_bad_request_response(
                data=serializer.errors, message='Invalid request data'
            )

        course_ids = serializer.validated_data['course_ids']
        department = serializer.validated_data['department']
        is_parallel = serializer.validated_data.get('is_parallel', False)

        # Validate courses exist
        courses = (
            Course.objects.filter(id__in=course_ids)
            .select_related('subject')
            .prefetch_related('professor', 'survey_template')
            .order_by('subject__name', 'id')
        )
        if courses.count() != len(course_ids):
            return get_bad_request_response(message='One or more courses not found')

        # Create session
        session_id = uuid.uuid4()
        SurveySession.objects.create(
            session_id=session_id, department=department, is_parallel=is_parallel
        )

        # Build response with courses, professors, and questions
        courses_data = []
        for course in courses:
            # Get questions from the course's survey template
            questions = []
            if course.survey_template:
                questions = SurveyQuestion.objects.filter(
                    template=course.survey_template
                )

            questions_data = QuestionSerializer(questions, many=True).data

            # Build professors list - each professor gets the same set of questions
            professors_data = []
            for professor in course.professor.all().order_by('full_name'):
                professors_data.append(
                    {
                        'professor_id': professor.id,
                        'professor_name': professor.full_name,
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

        courses_data.sort(key=lambda course: (course['subject_name'] or '', course['course_id']))
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

        # Validate session exists
        try:
            session = SurveySession.objects.get(session_id=session_id)
        except SurveySession.DoesNotExist:
            return get_bad_request_response(message='Session not found')

        # Create SurveyAnswer records
        answers_to_create = []
        for course_data in courses_data:
            course_id = course_data['course_id']

            try:
                course = Course.objects.get(id=course_id)
            except Course.DoesNotExist:
                return get_bad_request_response(
                    message=f'Course {course_id} not found'
                )

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

        return get_successful_response(
            data={'answers_count': len(answers_to_create)},
            message='Answers submitted successfully',
        )
