import json
from openai import OpenAI
from openai.types.chat import ChatCompletionUserMessageParam, ChatCompletionSystemMessageParam
from openai.types.shared_params import ResponseFormatJSONSchema

from config.constants import OPENAI_API_KEY, OPENAI_TEXT_MODEL, OPENAI_EMBED_MODEL
from hita.models import Performer
from .models import PerformerInsights
from .schemas import FEATURES_SCHEMA, chat_schema

client = OpenAI(api_key=OPENAI_API_KEY)


def extract_features_from_text(
    bio: str, experiences: list[dict], achievements: list[dict]
) -> dict:
    ex_lines = [
        f"{e.get('year')}|{e.get('show_type')}|{e.get('show_name')}|role={e.get('role_name')}|dir={e.get('director')}|fest={e.get('festival_name')}"
        for e in experiences or []
    ]
    ach_lines = [
        f"{a.get('year')}|{a.get('festival_name')}|{a.get('field')}|{a.get('position')}"
        for a in achievements or []
    ]
    user_msg = f"""Extract STRICT JSON. If unknown use null or [].
Schema:\n{json.dumps(FEATURES_SCHEMA, ensure_ascii=False)}
Rules:
- Do NOT invent facts.
- Normalize medium to THEATER/TV/MOVIE/RADIO.
Input:
BIO:
{bio or ""}

EXPERIENCES:
{chr(10).join(ex_lines)}

ACHIEVEMENTS:
{chr(10).join(ach_lines)}
Return ONLY JSON."""
    res = client.chat.completions.create(
        model=OPENAI_TEXT_MODEL,
        response_format=ResponseFormatJSONSchema(
            type="json_schema", json_schema=chat_schema
        ),
        temperature=0,
        messages=[ChatCompletionUserMessageParam(role="user", content=user_msg)],
    )
    return json.loads(res.choices[0].message.content)


def embed_text(text: str) -> list[float] | None:
    if not text:
        return None
    emb = client.embeddings.create(
        model=OPENAI_EMBED_MODEL,
        input=text,
    )
    return emb.data[0].embedding


def _llm_justify(query_text: str, performer: Performer, performer_insights: PerformerInsights) -> list[str]:
    # compact context
    skills = list(performer.skills_tags.values_list("name", flat=True))
    experiences = list(performer.experiences.order_by("-year").values("year", "show_name", "role_name", "show_type")[:5])
    ctx = {
        "query": query_text,
        "skills": skills,
        "features": performer_insights.features or {},
        "role_stats": performer_insights.role_stats or {},
        "recent_experiences": experiences,
    }
    msg = [
        ChatCompletionSystemMessageParam(content='Explain briefly why this performer matches the query. Use 2-3 short bullet reasons. No inventions.', role="system"),
        ChatCompletionUserMessageParam(content=json.dumps(ctx, ensure_ascii=False), role="user"),
    ]
    r = client.chat.completions.create(
        model=OPENAI_TEXT_MODEL,
        temperature=0,
        messages=msg
    )
    text = r.choices[0].message.content or ""
    # simple split; or ask model to return JSON bullets if you prefer
    reasons = [line.strip("-• ").strip() for line in text.split("\n") if line.strip()]
    return [x for x in reasons if x][:3]