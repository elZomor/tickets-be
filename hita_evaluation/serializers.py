from rest_framework import serializers

from hita_evaluation.models import Course, SurveyQuestion, Department, QuestionType


class CourseListSerializer(serializers.ModelSerializer):
    subject_name = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    credit_hours = serializers.SerializerMethodField()
    professor_name = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id',
            'subject_name',
            'category',
            'credit_hours',
            'professor_name',
            'department',
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
        professors = obj.professor.all()
        if not professors:
            return None
        return ' - '.join([p.full_name for p in professors])


# Session API Serializers


class StartSessionRequestSerializer(serializers.Serializer):
    course_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1, required=True
    )
    department = serializers.ChoiceField(choices=Department.choices, required=True)
    is_parallel = serializers.BooleanField(default=False)


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
    text_value = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class ProfessorAnswersSerializer(serializers.Serializer):
    professor_id = serializers.IntegerField()
    answers = AnswerSerializer(many=True)


class CourseAnswersSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    professors = ProfessorAnswersSerializer(many=True)


class SubmitAnswersRequestSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    courses = CourseAnswersSerializer(many=True)
