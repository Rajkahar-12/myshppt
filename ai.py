import json
import os

import requests


class AIError(Exception):
    """Shown to the user as a friendly message."""


SYSTEM_PROMPT = """You are an expert presentation designer who helps students.
Return ONLY valid JSON (no markdown, no extra text) in this shape:
{"title": str, "subtitle": str, "slides": [
  {"layout": "title|bullets|two-column|stat|quote|closing",
   "title": str,
   "subtitle": str,            // title and closing layouts
   "bullets": [str],           // bullets layout
   "left_title": str, "left": [str], "right_title": str, "right": [str],   // two-column layout
   "stat": {"value": str, "label": str},                                   // stat layout
   "quote": {"text": str, "author": str},                                  // quote layout
   "notes": str}               // 2-3 sentences the speaker can say
]}
Rules:
- Slide 1 layout is "title". The last slide layout is "closing".
- Middle slides mix "bullets" and "two-column". Use "stat" or "quote" at most once each,
  and ONLY if the number or quote is real and you are sure of it. Never invent facts.
- Max 5 bullets per slide, each under 14 words, clear and specific.
- Write for the given audience, tone and language.
- Exactly the requested number of slides."""


def demo_deck(topic):
    """Used when no API key is set, so you can still test the website."""
    return {
        "title": topic.title(),
        "subtitle": "Demo deck (add your API key for real content)",
        "demo": True,
        "slides": [
            {"layout": "title", "title": topic.title(), "subtitle": "Demo deck", "notes": "Welcome everyone."},
            {"layout": "bullets", "title": "Key Points", "bullets": ["First idea about " + topic, "Second idea", "Third idea"], "notes": "Explain each point."},
            {"layout": "two-column", "title": "Pros and Cons", "left_title": "Pros", "left": ["Easy", "Fast"], "right_title": "Cons", "right": ["Needs practice", "Needs time"], "notes": "Compare both sides."},
            {"layout": "stat", "title": "Did you know?", "stat": {"value": "100%", "label": "Demo number, not a real fact"}, "notes": ""},
            {"layout": "closing", "title": "Thank You", "subtitle": "Questions?", "notes": ""},
        ],
    }


def generate_deck(topic, slide_count, audience, language, tone):
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        return demo_deck(topic)

    model = os.getenv("AI_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    user_msg = (
        f"Topic: {topic}\nNumber of slides: {slide_count}\n"
        f"Audience: {audience}\nTone: {tone}\nLanguage: {language}"
    )
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
            },
            timeout=120,
        )
    except requests.RequestException:
        raise AIError("Could not reach the AI service. Check your internet and try again.")

    if r.status_code != 200:
        try:
            msg = r.json().get("error", {}).get("message", "")
        except ValueError:
            msg = ""
        raise AIError(f"AI service error ({r.status_code}). {msg} Check your API key and AI_MODEL in .env.")

    try:
        text = r.json()["choices"][0]["message"]["content"]
        deck = json.loads(text[text.index("{"): text.rindex("}") + 1])
        if not isinstance(deck.get("slides"), list) or not deck["slides"]:
            raise ValueError
    except (KeyError, IndexError, ValueError):
        raise AIError("The AI sent a broken answer. Please click Generate again.")
    return deck
