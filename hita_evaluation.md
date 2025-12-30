# HITA Evaluation Overview

## Domain Model

- **Department / Category / QuestionType / SemesterType**: Enum-like `TextChoices` that keep display labels for departments, subject categories, survey question types, and semester terms.
- **Professor / Subject / Semester**: Core academic catalog. Subjects belong to departments and categories, professors optionally to departments, and semesters track year/type plus the `is_current` flag.
- **SurveyTemplate / QuestionCategory / SurveyQuestion**: Template builder for surveys. Questions may be grouped into categories and linked to one or more templates with type + mandatory metadata.
- **Course**: Links a `Subject`, `Semester`, assigned `Professor`(s), and the `SurveyTemplate` used for evaluations.
- **SurveySession / SurveyAnswer**: Runtime data. Sessions represent a launched evaluation (department + parallel flag), while answers persist the question responses per session/course/professor.

## APIs

- `GET /departments`: Returns the non-general departments for front-end selection.
- `GET /courses`: Lists courses with flattened subject/professor details.
- `POST /sessions`: Starts a survey session. Validates course IDs, creates a UUID session, and returns a structure containing courses → professors → questions from the assigned template.
- `POST /sessions/submit`: Accepts a `session_id` plus nested course/professor answers, validates entity existence, and bulk creates `SurveyAnswer` rows.

## Admin Workflows

### Import Semester
- Accessible from the Semester changelist (“Import Semester” link).
- Upload an Excel file containing columns: `year`, `type`, `department`, `subject_name`, `category`, `credit_hours`, `professor`, `is_split`.
- First row sets/creates the `Semester` (marked `is_current=True`). Each row:
  - Ensures departments/categories/types are valid.
  - Creates/gets `Subject`s and `Professor`s (splitting professor names on `-`).
  - Finds the latest active `SurveyTemplate`.
  - Creates `Course` records; if `is_split` evaluates true and there are multiple professors, one course per professor, otherwise a single course with all professors attached.

### Import Survey Template
- Accessible from SurveyTemplate changelist.
- Upload an Excel with columns: `survey_name`, `version`, `question_category`, `question_text`, `question_type`, `is_mandatory`.
- First row creates an active `SurveyTemplate`.
- Each row creates/fetches a `QuestionCategory`, validates the question type, parses the mandatory flag, and creates `SurveyQuestion` linked to the template.

### Export Reports
- **SemesterAdmin → Export Department Report**: Select semesters, pick a department, and generate an Excel evaluation report for matching courses using `generate_evaluation_report`.
- **CourseAdmin → Export Evaluation Report**: Directly export selected courses to Excel.
- The generated Excel includes semester info, department, subject details, professor names, question category/type/text, evaluated answer, timestamp, and whether the session was parallel.

## Data Maintenance

- `python manage.py clear_hita_evaluation`: Custom management command that truncates app data in a safe order (answers → sessions → courses → semesters → survey definitions → catalog data).
- To reseed: import survey templates first, then import semesters to rebuild courses tied to the latest template.
