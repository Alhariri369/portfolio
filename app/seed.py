"""Idempotent seed script (run with: python -m app.seed).

Loads the owner's real CV data. Safe to re-run: rows are upserted by natural
keys, and testimonials / images / resume files are never seeded.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.models import (
    Certificate,
    Education,
    Experience,
    Profile,
    Project,
    Skill,
    SocialLink,
)

# The test suite walks this structure to verify every *_en string field has an
# idiomatic *_ar counterpart.
SEED: dict = {
    "profile": {
        "name": "Mohammed Alhariri",
        "title_en": "Backend Developer",
        "title_ar": "مطوّر خلفية",
        "tagline_en": "Backend Developer and Information Technology graduate focused on Python, FastAPI, and database management.",
        "tagline_ar": "مطوّر خلفية وخريج تقنية معلومات، تركيزي على بايثون وFastAPI وإدارة قواعد البيانات.",
        "summary_en": "Backend developer focused on Python, FastAPI, and database-driven applications. I build and ship web APIs end-to-end, from data modeling to deployment, with an emphasis on clean code and reliability.",
        "summary_ar": "مطوّر خلفية متخصص في بايثون وFastAPI والتطبيقات المعتمدة على قواعد البيانات. أبني الواجهات البرمجية وأطلقها من مرحلة نمذجة البيانات حتى النشر، مع التركيز على الكود النظيف والموثوقية العالية.",
        "location_en": "Yemen",
        "location_ar": "اليمن",
        "email": "moh.alhariri369@gmail.com",
        "phone": "+967 782 824 717",
        "github_url": "https://github.com/alhariri369",
    },
    "skills": [
        {"name_en": "Python", "name_ar": "بايثون", "category": "Languages", "sort_order": 10},
        {"name_en": "FastAPI", "name_ar": "FastAPI", "category": "Frameworks", "sort_order": 20},
        {"name_en": "Django", "name_ar": "Django", "category": "Frameworks", "sort_order": 21},
        {"name_en": "Tailwind CSS", "name_ar": "Tailwind CSS", "category": "Frameworks", "sort_order": 22},
        {"name_en": "Jinja2", "name_ar": "Jinja2", "category": "Templating", "sort_order": 30},
        {"name_en": "SQLAlchemy", "name_ar": "SQLAlchemy", "category": "Data", "sort_order": 40},
        {"name_en": "Pydantic", "name_ar": "Pydantic", "category": "Data", "sort_order": 41},
        {"name_en": "PostgreSQL", "name_ar": "PostgreSQL", "category": "Data", "sort_order": 42},
        {"name_en": "SQLite", "name_ar": "SQLite", "category": "Data", "sort_order": 43},
        {"name_en": "Redis", "name_ar": "Redis", "category": "Data", "sort_order": 44},
        {"name_en": "Supabase", "name_ar": "Supabase", "category": "Data", "sort_order": 45},
        {"name_en": "FAISS", "name_ar": "FAISS", "category": "AI / Vector search", "sort_order": 50},
        {"name_en": "MiniLM (ONNX)", "name_ar": "MiniLM (ONNX)", "category": "AI / Vector search", "sort_order": 51},
        {"name_en": "Cosine Similarity", "name_ar": "التشابه بجيب التمام", "category": "AI / Vector search", "sort_order": 52},
        {"name_en": "Gemini API", "name_ar": "Gemini API", "category": "AI / Vector search", "sort_order": 53},
        {"name_en": "Docker", "name_ar": "Docker", "category": "DevOps", "sort_order": 60},
        {"name_en": "Git", "name_ar": "Git", "category": "DevOps", "sort_order": 61},
        {"name_en": "GitHub", "name_ar": "GitHub", "category": "DevOps", "sort_order": 62},
    ],
    "experiences": [
        {
            "role_en": "Freelance Backend Developer",
            "role_ar": "مطوّر خلفية مستقل",
            "company_en": "Durrat Tarim",
            "company_ar": "درة تريم",
            "location_en": "Tarim, Yemen",
            "location_ar": "تريم، اليمن",
            "start_date": date(2026, 2, 1),
            "end_date": date(2026, 3, 1),
            "is_current": False,
            "description_en": "- Developed and deployed a custom web application for a retail client to digitize and manage their daily operations.\n- Built the backend using Django and integrated Supabase (PostgreSQL) for secure and reliable data storage.\n- Created a responsive UI with Tailwind CSS, working with the client to adjust the design based on their feedback.",
            "description_ar": "- طوّرت ونشرت تطبيق ويب مخصصًا لعميل في قطاع التجزئة لرقمنة عملياته اليومية وإدارتها.\n- بنيت الواجهة الخلفية باستخدام Django ودمجت Supabase (PostgreSQL) لتخزين البيانات بشكل آمن وموثوق.\n- أنشأت واجهة مستخدم متجاوبة باستخدام Tailwind CSS، وعملت مع العميل على تعديل التصميم بناءً على ملاحظاته.",
            "sort_order": 10,
        },
        {
            "role_en": "Backend Developer",
            "role_ar": "مطوّر خلفية",
            "company_en": "Seiyun University",
            "company_ar": "جامعة سيئون",
            "location_en": "Seiyun, Yemen",
            "location_ar": "سيئون، اليمن",
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 6, 1),
            "is_current": False,
            "description_en": "- Built the backend for a proposal-checking and project-archiving platform used by students, supervisors, department heads, and admins end-to-end.\n- Quantized an ONNX version of multilingual MiniLM to 8-bit to fit Railway's 1GB RAM limit; semantic similarity search over a FAISS index kept in sync with Supabase via a local SQLite cache.\n- Built endpoints comparing a submitted proposal against completed projects and returning similarity scores, paired with Gemini-generated feedback.\n- Load-tested the API to confirm 300+ concurrent reads and 10 concurrent writes within Railway's hosting limits; built with FastAPI, SQLAlchemy, and Pydantic, using async where supported.",
            "description_ar": "- بنيت الواجهة الخلفية لمنصة لفحص المقترحات وأرشفة المشاريع يستخدمها الطلاب والمشرفون ورؤساء الأقسام والإداريون من البداية إلى النهاية.\n- قلّصت نموذج MiniLM متعدد اللغات بصيغة ONNX إلى 8 بت ليتناسب مع حد الذاكرة البالغ 1 جيجابايت في Railway، مع بحث بالتشابه الدلالي عبر فهرس FAISS يبقى متزامنًا مع Supabase باستخدام ذاكرة SQLite محلية.\n- بنيت نقاط نهاية تقارن المقترح المقدَّم بالمشاريع المكتملة وتُرجع درجات التشابه، إلى جانب ملاحظات يولدها Gemini.\n- أجريت اختبارات تحميل على الواجهة البرمجية للتأكد من دعم أكثر من 300 قراءة متزامنة و10 عمليات كتابة متزامنة ضمن حدود استضافة Railway؛ بُنيت المنصة باستخدام FastAPI وSQLAlchemy وPydantic مع استخدام الأسلوب غير المتزامن حيثما كان مدعومًا.",
            "sort_order": 20,
        },
        {
            "role_en": "Python and Odoo Intern",
            "role_ar": "متدرب بايثون وأودو",
            "company_en": "NOMOW-SOFT",
            "company_ar": "NOMOW-SOFT",
            "location_en": "Yemen",
            "location_ar": "اليمن",
            "start_date": date(2025, 1, 1),
            "end_date": date(2025, 4, 1),
            "is_current": False,
            "description_en": "Completed a technical training program focused on Python and the basics of Odoo.",
            "description_ar": "أكملت برنامجًا تدريبيًا تقنيًا ركّز على بايثون وأساسيات أودو (Odoo).",
            "sort_order": 30,
        },
    ],
    "education": [
        {
            "institution_en": "Seiyun University",
            "institution_ar": "جامعة سيئون",
            "degree_en": "Bachelor of Science in Information Technology",
            "degree_ar": "بكالوريوس العلوم في تقنية المعلومات",
            "field_en": "Information Technology",
            "field_ar": "تقنية المعلومات",
            "start_date": date(2022, 1, 1),
            "end_date": date(2026, 1, 1),
            "description_en": "",
            "description_ar": "",
        }
    ],
    "certificates": [
        {
            "name_en": "Python Developer Certification",
            "name_ar": "شهادة مطوّر بايثون",
            "issuer_en": "freeCodeCamp",
            "issuer_ar": "freeCodeCamp",
            "issue_date": date(2026, 1, 1),
            "url": None,
        },
        {
            "name_en": "Introduction to Generative AI",
            "name_ar": "مقدمة في الذكاء الاصطناعي التوليدي",
            "issuer_en": "Google",
            "issuer_ar": "Google",
            "issue_date": date(2025, 6, 1),
            "url": None,
        },
    ],
    "projects": [
        {
            "slug": "graduation-projects-platform",
            "featured": True,
            "title_en": "Platform for Managing Graduation Projects",
            "title_ar": "منصة إدارة مشاريع التخرج",
            "summary_en": "Proposal-checking and project-archiving platform for students, supervisors, and admins.",
            "summary_ar": "منصة لفحص المقترحات وأرشفة المشاريع للطلاب والمشرفين والإداريين.",
            "description_en": "- Built the backend for a proposal-checking and project-archiving platform used by students, supervisors, department heads, and admins end-to-end.\n- Quantized an ONNX version of multilingual MiniLM to 8-bit to fit Railway's 1GB RAM limit; semantic similarity search over a FAISS index kept in sync with Supabase via a local SQLite cache.\n- Built endpoints comparing a submitted proposal against completed projects and returning similarity scores, paired with Gemini-generated feedback.\n- Load-tested the API to confirm 300+ concurrent reads and 10 concurrent writes within Railway's hosting limits; built with FastAPI, SQLAlchemy, and Pydantic, using async where supported.",
            "description_ar": "- بنيت الواجهة الخلفية لمنصة لفحص المقترحات وأرشفة المشاريع يستخدمها الطلاب والمشرفون ورؤساء الأقسام والإداريون من البداية إلى النهاية.\n- قلّصت نموذج MiniLM متعدد اللغات بصيغة ONNX إلى 8 بت ليتناسب مع حد الذاكرة البالغ 1 جيجابايت في Railway، مع بحث بالتشابه الدلالي عبر فهرس FAISS يبقى متزامنًا مع Supabase باستخدام ذاكرة SQLite محلية.\n- بنيت نقاط نهاية تقارن المقترح المقدَّم بالمشاريع المكتملة وتُرجع درجات التشابه، إلى جانب ملاحظات يولدها Gemini.\n- أجريت اختبارات تحميل على الواجهة البرمجية للتأكد من دعم أكثر من 300 قراءة متزامنة و10 عمليات كتابة متزامنة ضمن حدود استضافة Railway؛ بُنيت المنصة باستخدام FastAPI وSQLAlchemy وPydantic مع استخدام الأسلوب غير المتزامن حيثما كان مدعومًا.",
            "repo_url": None,
            "live_url": None,
            "sort_order": 10,
            "skills": ["FastAPI", "SQLAlchemy", "Pydantic", "Supabase", "FAISS", "MiniLM (ONNX)", "Gemini API"],
        },
        {
            "slug": "durrat-tarim-retail-app",
            "featured": False,
            "title_en": "Retail Operations Web App",
            "title_ar": "تطبيق ويب لإدارة عمليات التجزئة",
            "summary_en": "Custom web application digitizing daily operations for a retail client.",
            "summary_ar": "تطبيق ويب مخصص يرقمن العمليات اليومية لعميل في قطاع التجزئة.",
            "description_en": "- Developed and deployed a custom web application for a retail client to digitize and manage their daily operations.\n- Built the backend using Django and integrated Supabase (PostgreSQL) for secure and reliable data storage.\n- Created a responsive UI with Tailwind CSS, working with the client to adjust the design based on their feedback.",
            "description_ar": "- طوّرت ونشرت تطبيق ويب مخصصًا لعميل في قطاع التجزئة لرقمنة عملياته اليومية وإدارتها.\n- بنيت الواجهة الخلفية باستخدام Django ودمجت Supabase (PostgreSQL) لتخزين البيانات بشكل آمن وموثوق.\n- أنشأت واجهة مستخدم متجاوبة باستخدام Tailwind CSS، وعملت مع العميل على تعديل التصميم بناءً على ملاحظاته.",
            "repo_url": None,
            "live_url": None,
            "sort_order": 20,
            "skills": ["Django", "Supabase", "Tailwind CSS"],
        },
    ],
    "social_links": [
        {"platform": "GitHub", "url": "https://github.com/alhariri369", "sort_order": 10},
    ],
}


def _upsert(session: Session, model, natural_key: dict, values: dict):
    """Insert or update a single row keyed by natural_key."""
    obj = session.scalars(select(model).filter_by(**natural_key)).first()
    if obj is None:
        obj = model(**natural_key, **values)
        session.add(obj)
    else:
        for key, value in values.items():
            setattr(obj, key, value)
    session.flush()
    return obj


def seed(session: Session) -> None:
    """Apply the seed data to the given session (idempotent)."""
    profile = session.get(Profile, 1)
    if profile is None:
        profile = Profile(id=1, **SEED["profile"])
        session.add(profile)
    else:
        for key, value in SEED["profile"].items():
            setattr(profile, key, value)
    session.flush()

    skills: dict[str, Skill] = {}
    for item in SEED["skills"]:
        skill = _upsert(
            session,
            Skill,
            {"name_en": item["name_en"], "category": item["category"]},
            {"name_ar": item["name_ar"], "sort_order": item["sort_order"]},
        )
        skills[item["name_en"]] = skill

    for item in SEED["experiences"]:
        _upsert(
            session,
            Experience,
            {"company_en": item["company_en"], "role_en": item["role_en"]},
            {
                "company_ar": item["company_ar"],
                "role_ar": item["role_ar"],
                "location_en": item["location_en"],
                "location_ar": item["location_ar"],
                "start_date": item["start_date"],
                "end_date": item["end_date"],
                "is_current": item["is_current"],
                "description_en": item["description_en"],
                "description_ar": item["description_ar"],
                "sort_order": item["sort_order"],
            },
        )

    for item in SEED["education"]:
        _upsert(
            session,
            Education,
            {"institution_en": item["institution_en"], "degree_en": item["degree_en"]},
            {
                "institution_ar": item["institution_ar"],
                "degree_ar": item["degree_ar"],
                "field_en": item["field_en"],
                "field_ar": item["field_ar"],
                "start_date": item["start_date"],
                "end_date": item["end_date"],
                "description_en": item["description_en"],
                "description_ar": item["description_ar"],
            },
        )

    for item in SEED["certificates"]:
        _upsert(
            session,
            Certificate,
            {"name_en": item["name_en"], "issuer_en": item["issuer_en"]},
            {
                "name_ar": item["name_ar"],
                "issuer_ar": item["issuer_ar"],
                "issue_date": item["issue_date"],
                "url": item["url"],
            },
        )

    for item in SEED["projects"]:
        project = _upsert(
            session,
            Project,
            {"slug": item["slug"]},
            {
                "featured": item["featured"],
                "title_en": item["title_en"],
                "title_ar": item["title_ar"],
                "summary_en": item["summary_en"],
                "summary_ar": item["summary_ar"],
                "description_en": item["description_en"],
                "description_ar": item["description_ar"],
                "repo_url": item["repo_url"],
                "live_url": item["live_url"],
                "sort_order": item["sort_order"],
            },
        )
        # Add any missing skill links without removing manual additions.
        for skill_name in item["skills"]:
            skill = skills[skill_name]
            if skill not in project.skills:
                project.skills.append(skill)

    for item in SEED["social_links"]:
        _upsert(
            session,
            SocialLink,
            {"platform": item["platform"]},
            {"url": item["url"], "sort_order": item["sort_order"]},
        )

    session.commit()


def main() -> None:
    """Create tables (if needed) and run the seed against the configured DB."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed(session)
    print("Seed complete.")


if __name__ == "__main__":
    main()
