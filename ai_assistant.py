from __future__ import annotations

import html
import json
import os
import re
from typing import Any, Dict, Iterable, List

try:
    import bleach
except Exception:  # pragma: no cover - optional dependency fallback
    bleach = None

try:
    import markdown as markdown_lib
except Exception:  # pragma: no cover - optional dependency fallback
    markdown_lib = None

from .insights import analyze_run, dashboard_snapshot, journal_intelligence
from .models import ChatMessage, JournalEntry, PersonalityProfile, SimulationRun

DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_MAX_TOKENS = 700
DEFAULT_TEMPERATURE = 0.55
INPUT_MAX_CHARS = 1800
HISTORY_LIMIT = 10

ALLOWED_TAGS = [
    "a", "abbr", "b", "blockquote", "br", "code", "del", "details", "div", "em", "h1", "h2", "h3", "h4",
    "hr", "i", "li", "ol", "p", "pre", "span", "strong", "summary", "table", "tbody", "td", "th", "thead", "tr", "ul",
]
ALLOWED_ATTRS = {
    "a": ["href", "title", "rel", "target"],
    "abbr": ["title"],
    "code": ["class"],
    "pre": ["class"],
    "span": ["class"],
    "div": ["class"],
    "th": ["align"],
    "td": ["align"],
}


def clamp_text(text: str, limit: int = INPUT_MAX_CHARS) -> str:
    """Normalize and cap user text before it reaches the LLM."""
    text = (text or "").replace("\x00", "").strip()
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text[:limit]


def get_chat_config() -> Dict[str, Any]:
    def _int_env(name: str, fallback: int) -> int:
        try:
            return int(os.getenv(name, fallback))
        except (TypeError, ValueError):
            return fallback

    def _float_env(name: str, fallback: float) -> float:
        try:
            return float(os.getenv(name, fallback))
        except (TypeError, ValueError):
            return fallback

    return {
        "model": os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "max_tokens": max(128, min(_int_env("GROQ_MAX_TOKENS", DEFAULT_MAX_TOKENS), 2048)),
        "temperature": max(0.0, min(_float_env("GROQ_TEMPERATURE", DEFAULT_TEMPERATURE), 1.2)),
        "input_max_chars": max(400, min(_int_env("CHAT_INPUT_MAX_CHARS", INPUT_MAX_CHARS), 6000)),
        "has_api_key": bool(os.getenv("GROQ_API_KEY")),
    }


def markdown_to_safe_html(markdown_text: str) -> str:
    """Render markdown like a GPT chat answer, then sanitize it with Bleach."""
    markdown_text = (markdown_text or "").strip()
    if not markdown_text:
        return "<p>No response generated.</p>"

    if markdown_lib:
        raw_html = markdown_lib.markdown(
            markdown_text,
            extensions=["extra", "fenced_code", "tables", "nl2br", "sane_lists"],
            output_format="html5",
        )
    else:
        raw_html = "<p>" + html.escape(markdown_text).replace("\n", "<br>") + "</p>"

    if bleach:
        safe = bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, protocols=["http", "https", "mailto"], strip=True)
        safe = bleach.linkify(safe, callbacks=[_safe_link_attrs])
        return safe

    # If Bleach is not installed, fail safely by escaping content instead of returning raw HTML.
    return "<p>" + html.escape(markdown_text).replace("\n", "<br>") + "</p>"


def _safe_link_attrs(attrs, new=False):
    attrs[(None, "target")] = "_blank"
    attrs[(None, "rel")] = "nofollow noopener noreferrer"
    return attrs


def _parse_run(run: SimulationRun | None):
    if not run:
        return None
    try:
        return {
            "record": run,
            "profile_snapshot": json.loads(run.profile_snapshot_json),
            "selves": json.loads(run.result_json),
        }
    except json.JSONDecodeError:
        return None


def compact_user_context(user_id: int) -> Dict[str, Any]:
    profile = PersonalityProfile.query.filter_by(user_id=user_id).first()
    latest_run_record = SimulationRun.query.filter_by(user_id=user_id).order_by(SimulationRun.created_at.desc()).first()
    latest_run = _parse_run(latest_run_record)
    recent_entries = JournalEntry.query.filter_by(user_id=user_id).order_by(JournalEntry.created_at.desc()).limit(6).all()

    if not profile:
        profile_data = {
            "introversion": 50,
            "boldness": 50,
            "creativity": 50,
            "sleep_hours": 7,
            "work_hours": 6,
        }
        dashboard_ai = None
    else:
        profile_data = {
            "introversion": profile.introversion,
            "boldness": profile.boldness,
            "creativity": profile.creativity,
            "sleep_hours": profile.sleep_hours,
            "work_hours": profile.work_hours,
        }
        dashboard_ai = dashboard_snapshot(profile, latest_run, recent_entries)

    latest_analysis = analyze_run(latest_run["profile_snapshot"], latest_run["selves"]) if latest_run else None
    journal_ai = journal_intelligence(recent_entries)

    return {
        "profile": profile_data,
        "dashboard_ai": dashboard_ai,
        "latest_run": {
            "id": latest_run_record.id,
            "created_at": latest_run_record.created_at.strftime("%Y-%m-%d %H:%M"),
            "analysis": latest_analysis,
        }
        if latest_run_record and latest_analysis
        else None,
        "journal_intelligence": journal_ai,
        "recent_journal_titles": [e.title for e in recent_entries],
    }


def build_system_prompt(context: Dict[str, Any]) -> str:
    return f"""
You are Parallel Self AI Coach inside a student Flask project. Answer like a polished GPT-style assistant.
Use clear markdown, short headings, bullets when useful, and practical steps. Never claim to be a therapist or doctor.
Your job: help the user understand their profile, simulations, productivity routine, burnout risk, journal patterns, and project features.
Use the provided app context where relevant. If the user asks about code or presentation, explain in beginner-friendly language.
Keep answers concise but helpful. Prefer 3-6 bullets unless the user asks for detail.

Current personalized app context JSON:
{json.dumps(context, ensure_ascii=False, default=str)[:5000]}
""".strip()


def recent_chat_history(user_id: int, limit: int = HISTORY_LIMIT) -> List[Dict[str, str]]:
    rows = (
        ChatMessage.query.filter_by(user_id=user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return [{"role": row.role, "content": row.content[:2000]} for row in rows]


def generate_fallback_reply(user_message: str, context: Dict[str, Any]) -> str:
    profile = context.get("profile") or {}
    latest_run = context.get("latest_run") or {}
    journal = context.get("journal_intelligence") or {}
    lower = user_message.lower()

    if "plan" in lower or "routine" in lower or "schedule" in lower:
        return f"""
### 7-day improvement plan

Based on your current profile:

- **Sleep target:** keep sleep near **7–8 hours**. Your current value is **{profile.get('sleep_hours', 7)}h**.
- **Work/study load:** keep high-focus work inside your strongest energy window instead of spreading it all day.
- **Daily reflection:** write one short journal entry after study/work so the system can detect mood trends.
- **Recovery block:** add a small evening recovery task: walk, prayer/meditation, stretching, or no-screen time.
- **Next simulation:** generate a new run after changing sleep/work sliders to compare results.

> Groq API key is not configured yet, so this is the built-in offline coach response.
""".strip()

    if latest_run:
        best = latest_run.get("analysis", {}).get("best_overall", {})
        focus = latest_run.get("analysis", {}).get("best_focus", {})
        return f"""
### Latest run summary

- **Run:** #{latest_run.get('id')} generated on {latest_run.get('created_at')}
- **Best overall self:** **{best.get('type', 'Not available')}**
- **Best focus mode:** **{focus.get('type', 'Not available')}**
- **Recommended focus window:** **{focus.get('focus_window', {}).get('label', 'Not available')}**
- **Journal signal:** {journal.get('signal', 'No journal signal yet.')}

Use this page as your supervisor demo: it shows personalized simulation, stored history, charts, PDF export, admin analytics, and now a secure AI chatbot.

> Add `GROQ_API_KEY` in `.env` to enable live conversational responses.
""".strip()

    return f"""
### Parallel Self AI Coach

I can help you with:

- explaining your **profile and simulation scores**
- creating a **daily routine or 7-day action plan**
- summarizing your **latest run**
- preparing **presentation points for your supervisor**
- improving the project idea, frontend, or backend

Your current profile is: introversion **{profile.get('introversion', 50)}%**, boldness **{profile.get('boldness', 50)}%**, creativity **{profile.get('creativity', 50)}%**, sleep **{profile.get('sleep_hours', 7)}h**, work/study **{profile.get('work_hours', 6)}h**.

> Live Groq mode will turn on after you add `GROQ_API_KEY` to `.env`.
""".strip()


def call_groq(messages: List[Dict[str, str]], config: Dict[str, Any]) -> str:
    from groq import Groq

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    completion = client.chat.completions.create(
        model=config["model"],
        messages=messages,
        temperature=config["temperature"],
        max_completion_tokens=config["max_tokens"],
    )
    return completion.choices[0].message.content or "I could not generate a response."


def generate_assistant_reply(user_id: int, user_message: str) -> Dict[str, Any]:
    config = get_chat_config()
    user_message = clamp_text(user_message, config["input_max_chars"])
    context = compact_user_context(user_id)
    messages = [{"role": "system", "content": build_system_prompt(context)}]
    messages.extend(recent_chat_history(user_id, limit=HISTORY_LIMIT))
    messages.append({"role": "user", "content": user_message})

    used_live_model = False
    try:
        if config["has_api_key"]:
            reply_md = call_groq(messages, config)
            used_live_model = True
        else:
            reply_md = generate_fallback_reply(user_message, context)
    except Exception as exc:
        reply_md = (
            "### AI service fallback\n\n"
            "I could not reach the Groq API right now, so I used the built-in coach.\n\n"
            f"**Issue:** `{html.escape(str(exc))[:300]}`\n\n"
            + generate_fallback_reply(user_message, context)
        )

    reply_md = reply_md.strip()[:12000]
    return {
        "markdown": reply_md,
        "html": markdown_to_safe_html(reply_md),
        "model": config["model"] if used_live_model else "offline-fallback",
        "live": used_live_model,
        "config": config,
    }
