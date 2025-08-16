FEATURES_SCHEMA = {
    "languages": [],
    "accents": [],
    "genres": [],
    "techniques": [],
    "instruments": [],
    "sports": [],
    "role_history": [
        {
            "title": "",
            "year": None,
            "medium": "",  # THEATER|TV|MOVIE
            "role_name": "",
            "role_type": "",
            "director": "",
            "festival": "",
        }
    ],
    "awards": [{"name": "", "festival": "", "year": None}],
    "base_locations": [],
    "availability": [],
}

chat_schema = {
    "name": "actor_profile",
    "schema": {
        "type": "object",
        "properties": {
            "physical_attributes": {
                "type": "object",
                "properties": {
                    "eye_color": {"type": "string"},
                    "hair_color": {"type": "string"},
                    "skin_tone": {"type": "string"},
                    "body_type": {"type": "string"},
                },
                "required": [],
            },
            "skills": {"type": "array", "items": {"type": "string"}},
            "languages": {"type": "array", "items": {"type": "string"}},
            "experience_summary": {
                "type": "string",
                "description": "A short text summary of the actor's past work",
            },
            "notable_roles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "year": {"type": "integer"},
                        "title": {"type": "string"},
                        "role": {"type": "string"},
                        "category": {"type": "string"},
                    },
                    "required": ["year", "title"],
                },
            },
        },
        "required": [
            "physical_attributes",
            "skills",
            "languages",
            "experience_summary",
        ],
    },
}

# ---- replace your QUERY_SCHEMA with this ----
QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "gender": {"type": ["string", "null"], "enum": ["M", "F", None]},  # allow null
        "focus_terms": {"type": "array", "items": {"type": "string"}},
        "mediums": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["THEATER", "TV", "MOVIE", "RADIO", "DUBBING"],
            },
        },
        "w_skills": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "w_profile": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "min_year": {
            "type": ["integer", "null"]
        },  # optional value but still present (can be null)
    },
    "required": [
        "gender",
        "focus_terms",
        "mediums",
        "w_skills",
        "w_profile",
        "min_year",
    ],
    "additionalProperties": False,
}
