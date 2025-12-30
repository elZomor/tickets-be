from django.db import models


class Department(models.TextChoices):
    ACTING = 'ACTING', 'قسم التمثيل والإخراج المسرحي'
    DRAMA = 'DRAMA', 'قسم الدراما والنقد المسرحي'
    DECOR = 'DECOR', 'قسم الديكور المسرحي'
    TECHNIQUES = 'TECHNIQUES', 'قسم التقنيات المسرحية'
    GENERAL = 'GENERAL', 'عام'


class Category(models.TextChoices):
    MANDATORY_ACADEMY = 'MA', 'إجباري أكاديمية'
    MANDATORY_INSTITUTE = 'MI', 'إجباري معهد'
    MANDATORY_DEPARTMENT = 'MD', 'إجباري قسم'
    OPTIONAL_ACADEMY = 'OA', 'اختياري أكاديمية'
    OPTIONAL_INSTITUTE = 'OI', 'اختياري معهد'
    OPTIONAL_DEPARTMENT = 'OD', 'اختياري قسم'
    FREE_HOURS = 'FH', 'ساعات حرة'


class QuestionType(models.TextChoices):
    YES_NO = 'YN', 'نعم - لا'
    RATING = 'R', 'تقييم'
    SUGGESTION = 'S', 'اقتراح'
    TEXT = 'T', 'مقالي'


class Regulation(models.Model):
    name = models.CharField(max_length=100)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    is_latest = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class SemesterType(models.TextChoices):
    FALL = 'F', 'الفصل الأول'
    SPRING = 'G', 'الفصل الثاني'
    SUMMER = 'S', 'الصيف'


class ProfessorGrade(models.TextChoices):
    ASSOCIATE_PROFESSOR = 'ASSOC_PROF', 'أستاذ'
    LECTURER = 'LECT', 'دكتور'
    ASSISTANT_PROFESSOR = 'ASST_PROF', 'أستاذ مساعد دكتور'
    PROFESSOR = 'PROF', 'أستاذ دكتور'


class Professor(models.Model):
    full_name = models.CharField(max_length=100)
    department = models.CharField(
        max_length=20, choices=Department.choices, null=True, blank=True
    )
    grade = models.CharField(max_length=10, choices=ProfessorGrade.choices, blank=True)

    def __str__(self):
        return self.full_name


class Subject(models.Model):
    name = models.CharField(max_length=100)
    department = models.CharField(
        max_length=20, choices=Department.choices, null=True, blank=True
    )
    category = models.CharField(max_length=2, choices=Category.choices)
    credit_hours = models.IntegerField()

    def __str__(self):
        return self.name + ' - ' + self.department


class Semester(models.Model):
    year = models.IntegerField()
    type = models.CharField(max_length=1, choices=SemesterType.choices)
    is_current = models.BooleanField(default=True)

    def __str__(self):
        return str(self.year) + ' - ' + self.get_type_display()


class SurveyTemplate(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    version = models.IntegerField()
    name = models.CharField(max_length=100)

    def __str__(self):
        return 'V' + str(self.version) + ' - ' + self.created_at.__str__()


class Course(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    professor = models.ManyToManyField(Professor, through='CourseProfessor')
    semester = models.ForeignKey(to='Semester', on_delete=models.CASCADE)
    survey_template = models.ForeignKey(
        to='SurveyTemplate', on_delete=models.SET_NULL, null=True
    )
    is_parallel = models.BooleanField(default=False)
    regulations = models.ForeignKey(
        to='Regulation', on_delete=models.SET_NULL, null=True
    )

    def __str__(self):
        return (
            str(self.subject)
            + ': '
            + ' - '.join([p.full_name for p in self.professor.all()])
        )


class CourseProfessor(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE)
    grade = models.CharField(max_length=10, choices=ProfessorGrade.choices, blank=True)

    class Meta:
        unique_together = ('course', 'professor')

    def __str__(self):
        return f"{self.professor.full_name} - {self.grade}"


class QuestionCategory(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class SurveyQuestion(models.Model):
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=5, choices=QuestionType.choices, default=QuestionType.RATING.value
    )
    question_category = models.ForeignKey(
        to='QuestionCategory', null=True, on_delete=models.SET_NULL
    )
    template = models.ManyToManyField(to='SurveyTemplate')
    is_mandatory = models.BooleanField(default=True)

    def __str__(self):
        return self.question_text


class SessionStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'


class SurveySession(models.Model):
    session_id = models.UUIDField(unique=True)
    status = models.CharField(
        max_length=15, choices=SessionStatus.choices, default=SessionStatus.DRAFT
    )
    is_parallel = models.BooleanField(default=False)
    department = models.CharField(max_length=20, choices=Department.choices)
    regulation = models.ForeignKey(
        Regulation, on_delete=models.SET_NULL, null=True, blank=True
    )
    courses = models.ManyToManyField(Course, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)


class SurveyAnswer(models.Model):
    survey_session = models.ForeignKey(SurveySession, on_delete=models.CASCADE)
    course = models.ForeignKey(to='Course', on_delete=models.CASCADE)
    professor = models.ForeignKey(to='Professor', on_delete=models.CASCADE)
    question = models.ForeignKey(to='SurveyQuestion', on_delete=models.CASCADE)
    yes_no_answer = models.BooleanField(null=True, blank=True)
    rating_answer = models.IntegerField(null=True, blank=True)
    text_answer = models.TextField(null=True, blank=True)


class DashboardPermission(models.Model):
    """Proxy model to define dashboard permissions."""

    class Meta:
        managed = False  # No database table needed
        default_permissions = ()
        permissions = [
            ('can_view_dashboard', 'Can view evaluation dashboard'),
        ]
