from rest_framework import serializers

from hita_evaluation.models import (
    Course,
    SurveyQuestion,
    Department,
    QuestionType,
    Regulation,
)


class CourseListSerializer(serializers.ModelSerializer):
    subject_name = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    credit_hours = serializers.SerializerMethodField()
    professor_name = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    regulation_id = serializers.SerializerMethodField()
    regulation_name = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id',
            'subject_name',
            'category',
            'credit_hours',
            'professor_name',
            'department',
            'is_parallel',
            'regulation_id',
            'regulation_name',
        ]

    def get_subject_name(self, obj):
        return obj.subject.name if obj.subject else None

    def get_department(self, obj):
        return str(obj.subject.department) if obj.subject else None

    def get_category(self, obj):
        return obj.subject.get_category_display() if obj.subject else None

    def get_credit_hours(self, obj):
        return obj.subject.credit_hours if obj.subject else None

    def get_professor_name(self, obj):
        course_professors = (
            obj.courseprofessor_set.select_related('professor').order_by('professor__full_name')
        )
        if not course_professors:
            return None
        display_parts = []
        for cp in course_professors:
            professor = cp.professor
            if not professor:
                continue
            grade_label = cp.get_grade_display() if cp.grade else ''
            if grade_label:
                display_parts.append(f'{grade_label} {professor.full_name}')
            else:
                display_parts.append(professor.full_name)
        return ' - '.join(display_parts) if display_parts else None

    def get_regulation_id(self, obj):
        return obj.regulations.id if obj.regulations else None

    def get_regulation_name(self, obj):
        return obj.regulations.name if obj.regulations else None


class RegulationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Regulation
        fields = ['id', 'name', 'valid_from', 'valid_to', 'is_latest']


# Session API Serializers


class StartSessionRequestSerializer(serializers.Serializer):
    course_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1, required=True
    )
    department = serializers.ChoiceField(choices=Department.choices, required=True)
    regulation_id = serializers.IntegerField(required=True)
    is_parallel = serializers.BooleanField(default=False)

    def validate_regulation_id(self, value):
        if not Regulation.objects.filter(id=value).exists():
            raise serializers.ValidationError('Regulation not found')
        return value


class QuestionSerializer(serializers.ModelSerializer):
    category_id = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = SurveyQuestion
        fields = [
            'id',
            'question_text',
            'question_type',
            'is_mandatory',
            'category_id',
            'category_name',
        ]

    def get_category_id(self, obj):
        return obj.question_category.id if obj.question_category else None

    def get_category_name(self, obj):
        return obj.question_category.name if obj.question_category else None


class ProfessorWithQuestionsSerializer(serializers.Serializer):
    professor_id = serializers.IntegerField()
    professor_name = serializers.CharField()
    questions = QuestionSerializer(many=True)


class CourseWithProfessorsSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    subject_name = serializers.CharField()
    professors = ProfessorWithQuestionsSerializer(many=True)


class StartSessionResponseSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    courses = CourseWithProfessorsSerializer(many=True)


# Submit Answers Serializers


class AnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    yes_no_value = serializers.BooleanField(required=False, allow_null=True)
    rating_value = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=5
    )
    text_value = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class ProfessorAnswersSerializer(serializers.Serializer):
    professor_id = serializers.IntegerField()
    answers = AnswerSerializer(many=True)


class CourseAnswersSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    professors = ProfessorAnswersSerializer(many=True)


class SubmitAnswersRequestSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    courses = CourseAnswersSerializer(many=True)


# Dashboard Serializers


class DashboardDepartmentSerializer(serializers.Serializer):
    id = serializers.CharField()
    name_en = serializers.CharField()
    name_ar = serializers.CharField()


class DashboardCourseSerializer(serializers.Serializer):
    id = serializers.CharField()
    name_en = serializers.CharField()
    name_ar = serializers.CharField()
    department_id = serializers.CharField()


class DashboardProfessorSerializer(serializers.Serializer):
    id = serializers.CharField()
    name_en = serializers.CharField()
    name_ar = serializers.CharField()
    department_id = serializers.CharField()


class DashboardCategorySerializer(serializers.Serializer):
    id = serializers.CharField()
    name_en = serializers.CharField()
    name_ar = serializers.CharField()
    order_index = serializers.IntegerField()


class EvaluationAnswerSerializer(serializers.Serializer):
    evaluation_id = serializers.CharField()
    submitted_at = serializers.DateTimeField()
    department_id = serializers.CharField()
    department_name = serializers.CharField()
    course_id = serializers.CharField()
    course_name = serializers.CharField()
    professor_id = serializers.CharField()
    professor_name = serializers.CharField()
    regulation = serializers.CharField(allow_null=True)
    question_id = serializers.CharField()
    question_text = serializers.CharField()
    category_id = serializers.CharField()
    category_name = serializers.CharField()
    rating = serializers.IntegerField()
