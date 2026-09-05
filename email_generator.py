"""
email_generator.py
-------------------
Handles calling the LLM to generate personalized cold outreach emails,
including A/B variant generation. Supports Google Gemini or OpenAI as
the backend - pick whichever API key you have.
"""

import json
import re
import time


PROMPT_TEMPLATE = """You are an expert B2B sales copywriter who writes short,
high-converting, non-spammy cold outreach emails.

SENDER CONTEXT:
Product/Service: {product_description}
Target audience: {target_audience}
Sender name: {sender_name}
Sender company: {sender_company}
Desired tone/style: {tone}

PROSPECT DETAILS (personalize using these):
{prospect_details}

TASK:
Write {num_variants} DIFFERENT variant cold emails (label them Variant A, Variant B, etc.)
to this specific prospect, written in a {tone} tone throughout. Each variant must:
- Use a different angle/hook (e.g. Variant A = pain-point focused, Variant B = curiosity/social-proof focused, Variant C = direct value-prop focused)
- Reference at least one specific prospect detail provided above (name, company, role, pain point, industry, etc.)
- Be under 120 words
- Provide 3 DIFFERENT candidate subject lines for that same email body (no clickbait, no all-caps, no excessive punctuation), each scored with your own predicted open-rate likelihood from 1-100 based on how compelling/natural it is, with a one-line reason for the score
- End with a low-friction call-to-action (e.g. asking for a quick reply or a 15-min chat), not a pushy demand
- Sound human and conversational, NOT like a mass template
- Avoid spam-trigger words like "free", "guarantee", "act now", "click here", excessive exclamation marks, or ALL CAPS words

Return ONLY valid JSON in this exact structure, with no markdown fences and no extra commentary:
{{
  "variants": [
    {{
      "label": "Variant A",
      "angle": "short description of the angle used",
      "subject_options": [
        {{"subject": "subject line option 1", "predicted_open_rate": 45, "reason": "short reason for this score"}},
        {{"subject": "subject line option 2", "predicted_open_rate": 38, "reason": "short reason for this score"}},
        {{"subject": "subject line option 3", "predicted_open_rate": 30, "reason": "short reason for this score"}}
      ],
      "body": "email body text"
    }}
  ]
}}
"""


def build_prompt(product_description, target_audience, sender_name, sender_company,
                  prospect_details: dict, num_variants: int = 2, tone: str = "professional") -> str:
    details_str = "\n".join(f"- {k}: {v}" for k, v in prospect_details.items() if str(v).strip())
    return PROMPT_TEMPLATE.format(
        product_description=product_description,
        target_audience=target_audience,
        sender_name=sender_name or "N/A",
        sender_company=sender_company or "N/A",
        tone=tone,
        prospect_details=details_str if details_str else "No extra details provided.",
        num_variants=num_variants,
    )


def _extract_json(text: str) -> dict:
    """Strip markdown fences if present and parse JSON, with a fallback regex grab."""
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text.strip(), flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text.strip()).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def call_gemini(api_key: str, prompt: str, model: str = "gemini-flash-lite-latest",
                 max_retries: int = 3) -> str:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    gen_model = genai.GenerativeModel(model)

    last_error = None
    for attempt in range(max_retries):
        try:
            response = gen_model.generate_content(prompt)
            return response.text
        except Exception as e:
            last_error = e
            # If it's a rate-limit (429) error, wait and retry with backoff.
            if "429" in str(e) or "quota" in str(e).lower():
                time.sleep(15 * (attempt + 1))
                continue
            raise
    raise last_error


def call_openai(api_key: str, prompt: str, model: str = "gpt-4o-mini") -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )
    return response.choices[0].message.content


def generate_email_variants(provider: str, api_key: str, product_description: str,
                             target_audience: str, sender_name: str, sender_company: str,
                             prospect_details: dict, num_variants: int = 2,
                             tone: str = "professional") -> list:
    """
    Calls the selected LLM provider and returns a list of variant dicts:
    [{"label": ..., "angle": ..., "subject": ..., "body": ...}, ...]
    """
    prompt = build_prompt(product_description, target_audience, sender_name,
                           sender_company, prospect_details, num_variants, tone)

    if provider == "gemini":
        raw_text = call_gemini(api_key, prompt)
    elif provider == "openai":
        raw_text = call_openai(api_key, prompt)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    data = _extract_json(raw_text)
    variants = data.get("variants", [])
    return [_normalize_variant(v) for v in variants]


def _normalize_variant(variant: dict) -> dict:
    """
    Ensures every variant has:
    - subject_options: list of {subject, predicted_open_rate, reason}, sorted best-first
    - subject: convenience field = the top-scored subject line (for display/export defaults)
    """
    options = variant.get("subject_options") or []
    # Fallback for older-shaped responses that only returned a single "subject" string.
    if not options and variant.get("subject"):
        options = [{"subject": variant["subject"], "predicted_open_rate": 50, "reason": "Only option generated."}]

    cleaned_options = []
    for opt in options:
        cleaned_options.append({
            "subject": opt.get("subject", "").strip(),
            "predicted_open_rate": opt.get("predicted_open_rate", 0),
            "reason": opt.get("reason", ""),
        })
    cleaned_options.sort(key=lambda o: o.get("predicted_open_rate", 0), reverse=True)

    variant["subject_options"] = cleaned_options
    variant["subject"] = cleaned_options[0]["subject"] if cleaned_options else ""
    return variant
