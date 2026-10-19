import datetime

from django.db import migrations

VERSION = '1.0'

CONTENT = {
    "title": {
        "ar": "الشروط والأحكام وسياسة النشر",
        "en": "Terms & Conditions and Publishing Policy",
        "ro": "Termeni și condiții și politica de publicare",
    },
    "sections": [
        {
            "heading": {
                "ar": "تمهيد واتفاقية الاستخدام",
                "en": "Introduction and Usage Agreement",
                "ro": "Introducere și acord de utilizare",
            },
            "paragraphs": [
                {
                    "ar": "يُعد استخدامك لمنصة وموقع «الضلع الثالث» موافقة صريحة وكاملة على كافة البنود الواردة في هذه الوثيقة. إذا كنت لا توافق على هذه الشروط، يُرجى الامتناع عن استخدام المنصة أو التسجيل فيها.",
                    "en": "Your use of the Third Side platform and website constitutes explicit and full acceptance of every clause in this document. If you do not agree to these terms, please refrain from using the platform or registering on it.",
                    "ro": "Utilizarea platformei și a site-ului A Treia Latură (Third Side) reprezintă acceptarea explicită și deplină a tuturor clauzelor din acest document. Dacă nu sunteți de acord cu acești termeni, vă rugăm să nu utilizați platforma și să nu vă înregistrați pe ea.",
                }
            ],
        },
        {
            "heading": {
                "ar": "حقوق الملكية الفكرية والنشر",
                "en": "Intellectual Property and Publishing Rights",
                "ro": "Drepturi de proprietate intelectuală și de publicare",
            },
            "paragraphs": [
                {
                    "ar": "كافة المقالات، الدراسات النقدية، التصاميم البصرية، الأيقونات، العلامات التجارية، ومحتوى البودكاست والفيديو المنشور على الموقع هي حقوق ملكية حصرية لمنصة «الضلع الثالث» أو لكُتّابها ومترجميها بموجب عقود النشر.",
                    "en": "All articles, critical studies, visual designs, icons, trademarks, and podcast and video content published on the site are the exclusive property of the Third Side platform or of its writers and translators under publishing contracts.",
                    "ro": "Toate articolele, studiile critice, designurile vizuale, pictogramele, mărcile comerciale și conținutul de podcast și video publicate pe site sunt proprietatea exclusivă a platformei Third Side sau a autorilor și traducătorilor săi, în baza contractelor de publicare.",
                },
                {
                    "ar": "يُحظر نسخ، إعادة توزيع، اقتباس أجزاء جوهرية، أو ترجمة أي مادة دون الإشارة الصريحة للمنصة ووضع الرابط المباشر للمقال الأصلي، مع منع الاستغلال التجاري للمحتوى منعاً باتاً دون إذن كتابي مسبق.",
                    "en": "Copying, redistributing, quoting substantial parts of, or translating any material is prohibited without explicitly crediting the platform and linking directly to the original article. Commercial exploitation of the content is strictly prohibited without prior written permission.",
                    "ro": "Este interzisă copierea, redistribuirea, citarea unor părți substanțiale sau traducerea oricărui material fără menționarea explicită a platformei și fără un link direct către articolul original. Exploatarea comercială a conținutului este strict interzisă fără acord scris prealabil.",
                },
            ],
        },
        {
            "heading": {
                "ar": "معايير وسياسات قبول المواد والمساهمات (Submission Policy)",
                "en": "Standards and Policies for Accepting Material and Contributions (Submission Policy)",
                "ro": "Standarde și politici de acceptare a materialelor și contribuțiilor (Submission Policy)",
            },
            "paragraphs": [
                {
                    "ar": "ترحب المنصة بإسهامات النقاد، الأكاديميين، والمترجمين وفق المعايير التالية:",
                    "en": "The platform welcomes contributions from critics, academics and translators according to the following standards:",
                    "ro": "Platforma primește cu bucurie contribuțiile criticilor, ale academicienilor și ale traducătorilor, în conformitate cu următoarele standarde:",
                }
            ],
            "bullets": [
                {
                    "ar": "أن يتسم الطرح بالمنهجية العلمية والنزاهة النقدية والموضوعية التامة.",
                    "en": "The argument must be marked by scholarly method, critical integrity and complete objectivity.",
                    "ro": "Argumentația trebuie să se distingă prin metodă științifică, integritate critică și obiectivitate deplină.",
                },
                {
                    "ar": "خلو المادة من أي تجريح شخصي، عبارات كراهية، تنمر، أو تشهير بالمبدعين وصناع الأعمال الفنية.",
                    "en": "The material must be free of personal attacks, hate speech, bullying, or defamation of artists and the makers of artistic works.",
                    "ro": "Materialul trebuie să fie lipsit de atacuri la persoană, discurs de ură, bullying sau defăimare la adresa creatorilor și a autorilor operelor artistice.",
                },
                {
                    "ar": "أصالة المحتوى؛ وتتحمل جهة الإرسال والكاتب المسؤولية القانونية والأدبية الكاملة عن أصالة نصوصه ومراعاة حقوق الاقتباس والمصادر.",
                    "en": "The content must be original; the submitting party and the writer bear full legal and moral responsibility for the originality of their texts and for respecting quotation rights and sources.",
                    "ro": "Conținutul trebuie să fie original; cel care îl trimite și autorul poartă întreaga răspundere juridică și morală pentru originalitatea textelor și pentru respectarea drepturilor de citare și a surselor.",
                },
                {
                    "ar": "تحتفظ هيئة التحرير بحق التدقيق اللغوي وتنسيق العناوين بما يتماشى مع السياسة التحريرية للمنصة دون الإخلال بالمضمون.",
                    "en": "The editorial board reserves the right to proofread and to format headings in line with the platform's editorial policy, without altering the substance.",
                    "ro": "Colegiul editorial își rezervă dreptul de a face corectura lingvistică și de a formata titlurile în acord cu politica editorială a platformei, fără a modifica conținutul.",
                },
            ],
        },
        {
            "heading": {
                "ar": "سياسة التعليقات وحسابات القراء (Community Guidelines)",
                "en": "Comments and Reader Accounts Policy (Community Guidelines)",
                "ro": "Politica privind comentariile și conturile cititorilor (Community Guidelines)",
            },
            "paragraphs": [
                {
                    "ar": "تتيح المنصة خاصية التعليق والتقييم لفتح باب السجال الثقافي؛ ويُشترط أن تكون التعليقات ذات صلة بالمادة النقدية ومصاغة بأسلوب لائق. تحتفظ إدارة المنصة بالحق الكامل في حذف أي تعليق مسيء أو حظر الحسابات التي تنتهك قواعد الحوار دون إشعار مسبق.",
                    "en": "The platform offers commenting and rating to open the door to cultural debate; comments must be relevant to the critical piece and phrased respectfully. The platform's management reserves the full right to delete any offensive comment or ban accounts that violate the rules of dialogue, without prior notice.",
                    "ro": "Platforma oferă funcția de comentarii și evaluare pentru a deschide dezbaterea culturală; comentariile trebuie să aibă legătură cu materialul critic și să fie formulate într-un mod decent. Conducerea platformei își rezervă dreptul deplin de a șterge orice comentariu ofensator sau de a bloca conturile care încalcă regulile dialogului, fără notificare prealabilă.",
                }
            ],
        },
        {
            "heading": {
                "ar": "حقوق النصوص والسيناريوهات (المتجر والمزادات)",
                "en": "Rights to Texts and Scripts (Store and Auctions)",
                "ro": "Drepturile asupra textelor și scenariilor (magazin și licitații)",
            },
            "paragraphs": [
                {
                    "ar": "عند إتاحة المنصة لتداول أو استعراض نصوص مسرحية أو سيناريوهات، تلتزم المنصة بتوثيق حقوق المؤلف الأصلية؛ وتعتبر أي تعاملات لاحقة بين الأطراف محكومة باتفاقيات الملكية الفكرية المعتمدة محلياً ودولياً.",
                    "en": "When the platform makes play texts or scripts available for trade or viewing, it undertakes to document the original author's rights; any later dealings between the parties are governed by the intellectual property agreements recognized locally and internationally.",
                    "ro": "Atunci când platforma pune la dispoziție texte de teatru sau scenarii pentru schimb sau consultare, ea se angajează să documenteze drepturile de autor originale; orice tranzacții ulterioare între părți sunt guvernate de acordurile de proprietate intelectuală recunoscute la nivel local și internațional.",
                }
            ],
        },
        {
            "heading": {
                "ar": "التعديلات القانونية",
                "en": "Legal Amendments",
                "ro": "Modificări juridice",
            },
            "paragraphs": [
                {
                    "ar": "تحتفظ إدارة منصة «الضلع الثالث» بحق تعديل أو تحديث هذه الشروط في أي وقت لمواكبة التطورات التقنية أو التنظيمية، وتسري التعديلات فور نشرها على هذه الصفحة.",
                    "en": "The management of the Third Side platform reserves the right to amend or update these terms at any time to keep pace with technical or regulatory developments. Amendments take effect as soon as they are published on this page.",
                    "ro": "Conducerea platformei Third Side își rezervă dreptul de a modifica sau actualiza acești termeni în orice moment, pentru a ține pasul cu evoluțiile tehnice sau de reglementare. Modificările intră în vigoare imediat ce sunt publicate pe această pagină.",
                }
            ],
        },
    ],
}


def add_first_terms(apps, schema_editor):
    """First published Terms & Conditions. Never overwrites an existing row:
    published terms are immutable, later changes are new versions."""
    TermsVersion = apps.get_model('third_side', 'TermsVersion')
    TermsVersion.objects.get_or_create(
        version=VERSION,
        defaults={
            'effective_date': datetime.date(2026, 10, 1),
            'is_published': True,
            'content': CONTENT,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('third_side', '0013_terms'),
    ]

    operations = [
        migrations.RunPython(add_first_terms, migrations.RunPython.noop),
    ]
