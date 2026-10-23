"""Claude calls: extract memories and write replies."""
import json
import os
from datetime import date, datetime, timedelta, timezone
from functools import cache

import anthropic
from dotenv import load_dotenv

load_dotenv()

CHAT_MODEL = "claude-sonnet-5-5"  # replies
FAST_MODEL = "claude-haiku-5-5"   # background work (extraction)
TYPES = ["preference", "fact", "goal", "mood"]

EXTRACT_PROMPT = """You pull out things worth remembering about the user from their message.
Today is {today}.

Return ONLY a JSON array, no other text. Each item looks like:
{{"type": "preference" | "fact" | "goal" | "mood", "content": "short sentence about the user", "expires_on": "YYYY-MM-DD" or null}}

Rules:
- preference: likes, dislikes, habits. Example: "Studies best at night".
- fact: things about the user's life. If tied to a date (exam, trip), set expires_on to that date.
- goal: something the user wants to achieve.
- mood: how the user feels right now.
- Write content in third person, like "Is vegetarian".
- NEVER store passwords, phone numbers, emails, addresses, bank or ID numbers.
- Questions, requests (like "plan my week") and small talk have nothing to remember: return [].
"""

REPLY_PROMPT = """You are MemoMate, a friendly diary and planning buddy.
Today is {today}.

What you remember about the user:
{memories}

Use these naturally when they matter, especially when planning. Don't list them back unless asked.
Keep replies short and warm."""


@cache
def _client():
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _today():
    return date.today().strftime("%A, %Y-%m-%d")


def parse_memories(text):
    """Turn Claude's answer into a list of memory dicts. Bad JSON -> []."""
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [
        m for m in data
        if isinstance(m, dict) and m.get("type") in TYPES
        and isinstance(m.get("content"), str) and m["content"].strip()
    ]


def expires_at(mem, now):
    """PRD expiry rules: moods 3 days, dated facts the day after, others never."""
    if mem["type"] == "mood":
        return now + timedelta(days=3)
    if mem["type"] == "fact" and mem.get("expires_on"):
        try:
            d = date.fromisoformat(mem["expires_on"])
        except (TypeError, ValueError):
            return None
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc) + timedelta(days=1)
    return None


def extract_memories(message):
    resp = _client().messages.create(
        model=FAST_MODEL,
        max_tokens=1024,
        system=EXTRACT_PROMPT.format(today=_today()),
        messages=[{"role": "user", "content": message}],
    )
    return parse_memories(resp.content[0].text)


def reply(history, memories):
    """history: list of {"role", "content"} dicts ending with the new user message."""
    known = "\n".join(f"- ({m['type']}) {m['content']}" for m in memories) or "(nothing yet)"
    resp = _client().messages.create(
        model=CHAT_MODEL,
        max_tokens=1024,
        system=REPLY_PROMPT.format(today=_today(), memories=known),
        messages=[{"role": m["role"], "content": m["content"]} for m in history],
    )
    return resp.content[0].text


if __name__ == "__main__":
    # Quick self-check, no API calls: python brain.py
    assert parse_memories('```json\n[{"type":"mood","content":"Tired"}]\n```') == [{"type": "mood", "content": "Tired"}]
    assert parse_memories("not json") == []
    assert parse_memories('[{"type":"secret","content":"x"}]') == []
    now = datetime(2026, 10, 24, tzinfo=timezone.utc)
    assert expires_at({"type": "mood"}, now) == datetime(2026, 10, 27, tzinfo=timezone.utc)
    assert expires_at({"type": "fact", "expires_on": "2026-10-30"}, now) == datetime(2026, 10, 31, tzinfo=timezone.utc)
    assert expires_at({"type": "preference", "expires_on": "2026-10-30"}, now) is None
    assert expires_at({"type": "fact", "expires_on": "Friday"}, now) is None
    print("brain.py self-check passed")
