import json

from django.db import transaction, connection
from django.utils.timezone import now

from config.constants import ACTOGRAM_FE_URL
from .models import PerformerInsights
from hita.models import Performer
from .extractors import (
    extract_features_from_text,
    embed_text,
    _llm_justify,
    parse_ar_query_to_schema,
)


def _compute_role_stats(experiences: list[dict]) -> dict:
    years = [e.get("year") for e in experiences or [] if e.get("year")]
    counts = {"THEATER": 0, "TV": 0, "MOVIE": 0, "RADIO": 0, "DUBBING": 0}
    dirs = {}
    fest = 0
    first_year = min(years) if years else None
    last_year = max(years) if years else None
    for e in experiences or []:
        m = (e.get("show_type") or "").upper()
        if m in counts:
            counts[m] += 1
        if e.get("director"):
            dirs[e["director"]] = dirs.get(e["director"], 0) + 1
        if e.get("festival_name"):
            fest += 1
    top_directors = sorted(dirs.items(), key=lambda x: x[1], reverse=True)[:5]
    return {
        "counts_by_medium": counts,
        "years_active": (last_year - first_year + 1) if first_year and last_year else 0,
        "first_year": first_year,
        "last_year": last_year,
        "top_directors": [{"name": d, "count": c} for d, c in top_directors],
        "festival_count": fest,
        "generated_at": now().isoformat(),
    }


@transaction.atomic
def enrich_performer_from_raw(performer: Performer) -> dict:
    bio = performer.biography or ""
    experiences = list(
        performer.experiences.values(
            "year", "show_type", "show_name", "role_name", "director", "festival_name"
        )
    )
    achievements = list(
        performer.achievements.values("year", "festival_name", "field", "position")
    )
    skills_tags = list(performer.skills_tags.values_list("name", flat=True))
    features = extract_features_from_text(
        bio=bio, experiences=experiences, achievements=achievements
    )
    role_stats = _compute_role_stats(experiences)
    profile_text = "\n".join(
        [
            bio,
            *(
                f"{e.get('year')} {(e.get('show_type') or '').upper()} {e.get('show_name')} {e.get('role_name') or ''}"
                for e in experiences
            ),
            *(
                f'{a.get("year")} {a.get("festival_name") or ""} {a.get("field") or ""} {a.get("position") or ""}'
                for a in achievements
            ),
        ]
    )
    skills_text = json.dumps(
        {
            "skills_tags": skills_tags,
            "features": {
                "languages": features["languages"],
                "accents": features["accents"],
                "genres": features["genres"],
                "techniques": features["techniques"],
                "instruments": features["instruments"],
                "sports": features["sports"],
            },
        },
        ensure_ascii=False,
    )

    vec_profile = embed_text(profile_text)
    vec_skills = embed_text(skills_text)

    insights, is_created = PerformerInsights.objects.get_or_create(performer=performer)
    insights.features = features
    insights.role_stats = role_stats
    if vec_profile:
        insights.vec_profile = vec_profile
    if vec_skills:
        insights.vec_skills = vec_skills
    insights.source_version = (
        "v1" if is_created else f'v${(int(insights.source_version or 0) + 1)}'
    )
    insights.save()

    return {"ok": True, "features": features, "role_stats": role_stats}


def _vector_literal(vec: list[float]) -> str:
    # pgvector text format: "[v1, v2, v3, ...]"
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


def semantic_search_performers(query: str, limit: int = 3):
    configurations = parse_ar_query_to_schema(query) or {}
    gender = configurations.get("gender")
    terms = configurations.get("focus_terms") or []
    mediums = configurations.get("mediums") or []
    w_skills = float(configurations.get("w_skills", 0.8))
    w_profile = float(configurations.get("w_profile", 0.2))
    skill_query = " ".join(terms) if terms else query
    q_vec_skills = embed_text(skill_query)
    q_vec_profile = embed_text(query)
    if not q_vec_skills or not q_vec_profile:
        return []

    query_literal_skills = _vector_literal(q_vec_skills)
    query_literal_profile = _vector_literal(q_vec_profile)

    params = [
        query_literal_skills,
        w_skills,
        query_literal_profile,
        w_profile,
        query_literal_skills,
        w_skills,
        query_literal_profile,
        w_profile,
    ]
    gender_clause = ""
    if gender in ("F", "M"):
        gender_clause = "AND hm.gender = %s"
        params.append(gender)
    medium_bonus_sql = ""
    if mediums:
        bonuses = [
            f"LEAST(COALESCE((i.role_stats->'counts_by_medium'->>'{m}')::int,0) * 0.02, 0.10)"
            for m in mediums
        ]
        medium_bonus_sql = " - (" + " + ".join(bonuses) + ")"

    params.append(limit)
    sql = f"""
            SELECT
                p.id,
                hm.first_name || ' ' || hm.last_name AS full_name,
                (
                  ((i.vec_skills  <=> %s::vector) * %s) +
                  ((i.vec_profile <=> %s::vector) * %s)
                ){medium_bonus_sql} AS combo_dist,
                1 - (
                  ((i.vec_skills  <=> %s::vector) * %s) +
                  ((i.vec_profile <=> %s::vector) * %s)
                ) AS combo_score
            FROM ai_performerinsights i
            JOIN hita_performer p ON p.id = i.performer_id
            JOIN hita_hitamember hm ON hm.id = p.hita_member_id
            WHERE i.vec_skills IS NOT NULL
              AND i.vec_profile IS NOT NULL
              {gender_clause}
            ORDER BY combo_dist ASC
            LIMIT %s
        """
    with connection.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    out = []
    for pid, full_name, _dist, score in rows:
        perf = Performer.objects.get(id=pid)
        ins = PerformerInsights.objects.get(performer_id=pid)
        reasons = _llm_justify(query, perf, ins)
        out.append(
            {
                "url": ACTOGRAM_FE_URL + '/artists/' + perf.hita_member.user.username,
                "id": pid,
                "full_name": full_name,
                "score": float(score),
                "why": reasons,
            }
        )
    return out
