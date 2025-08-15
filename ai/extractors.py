import json
from openai import OpenAI
from openai.types.chat import ChatCompletionUserMessageParam
from openai.types.shared_params import ResponseFormatJSONSchema

from config.constants import OPENAI_API_KEY, OPENAI_TEXT_MODEL, OPENAI_EMBED_MODEL
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
        messages=ChatCompletionUserMessageParam(role="user", content=user_msg),
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
