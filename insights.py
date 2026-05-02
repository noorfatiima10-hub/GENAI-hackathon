from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List


def avg(values: Iterable[float]) -> float:
    values = list(values)
    return round(mean(values), 1) if values else 0.0


def _stability(values: List[float]) -> float:
    if not values:
        return 0.0
    variance = pstdev(values)
    return round(max(0.0, 100.0 - variance * 2.2), 1)


def _peak_window(values: List[float], width: int = 3) -> Dict[str, Any]:
    if not values:
        return {"start": 0, "end": width, "label": "00:00–03:00", "score": 0}
    best_start = 0
    best_score = -1
    for start in range(0, max(1, len(values) - width + 1)):
        score = sum(values[start : start + width])
        if score > best_score:
            best_start = start
            best_score = score
    end = min(best_start + width, 24)
    return {
        "start": best_start,
        "end": end,
        "label": f"{best_start:02d}:00–{end:02d}:00",
        "score": round(best_score / max(width, 1), 1),
    }


def classify_archetype(profile: Dict[str, Any]) -> str:
    intro = profile.get("introversion", 50)
    bold = profile.get("boldness", 50)
    creative = profile.get("creativity", 50)
    sleep = profile.get("sleep_hours", 7)
    work = profile.get("work_hours", 6)

    if creative >= 70 and work <= 7:
        return "Creative Explorer"
    if bold >= 70 and intro <= 45:
        return "Public-Facing Driver"
    if intro >= 70 and work >= 6:
        return "Deep Work Strategist"
    if sleep >= 8 and 4 <= work <= 7:
        return "Balanced Recovery Builder"
    if work >= 9:
        return "High-Pressure Operator"
    return "Adaptive Generalist"


def journal_intelligence(entries: List[Any]) -> Dict[str, Any]:
    if not entries:
        return {
            "count": 0,
            "streak": 0,
            "dominant_mood": "No data",
            "sentiment_score": 50,
            "signal": "Start journaling to unlock reflection intelligence.",
            "themes": [],
        }

    entries_sorted = sorted(entries, key=lambda e: e.created_at, reverse=True)
    moods = [getattr(e, "mood", "neutral") for e in entries_sorted]
    dominant_mood = Counter(moods).most_common(1)[0][0].title()

    positive = {"good", "great", "happy", "progress", "calm", "win", "focused", "better", "productive", "confident"}
    negative = {"stress", "stressed", "sad", "tired", "drained", "anxious", "overwhelmed", "burnout", "pressure", "bad"}
    theme_words = Counter()
    score = 50
    for entry in entries_sorted[:12]:
        text = f"{getattr(entry, 'title', '')} {getattr(entry, 'content', '')}".lower()
        words = [w.strip('.,!?;:()[]{}"\'') for w in text.split() if len(w) > 3]
        theme_words.update(words)
        score += sum(3 for w in words if w in positive)
        score -= sum(3 for w in words if w in negative)

    score = int(max(0, min(100, score)))

    dates = sorted({e.created_at.date() for e in entries_sorted}, reverse=True)
    streak = 0
    cursor = date.today()
    for d in dates:
        if d == cursor or d == cursor - timedelta(days=1 if streak == 0 else 0):
            streak += 1
            cursor = d - timedelta(days=1)
        elif d == cursor:
            streak += 1
            cursor = cursor - timedelta(days=1)
        else:
            if d < cursor:
                break

    filtered_themes = [w for w, c in theme_words.most_common(8) if w not in {"with", "from", "that", "this", "have", "work", "today", "about", "your"}]
    signal = (
        "Recent journal tone looks healthy and reflective."
        if score >= 60
        else "Journal tone suggests pressure is building; add recovery blocks and lighter work windows."
        if score <= 40
        else "Journal tone is mixed; keep tracking patterns to identify stable habits."
    )
    return {
        "count": len(entries_sorted),
        "streak": streak,
        "dominant_mood": dominant_mood,
        "sentiment_score": score,
        "signal": signal,
        "themes": filtered_themes[:5],
    }


def analyze_run(profile: Dict[str, Any], selves: List[Dict[str, Any]]) -> Dict[str, Any]:
    enriched = []
    sleep = profile.get("sleep_hours", 7)
    work = profile.get("work_hours", 6)
    intro = profile.get("introversion", 50)
    bold = profile.get("boldness", 50)
    creative = profile.get("creativity", 50)

    burnout_base = max(0, (work - 7) * 8) + max(0, (6 - sleep) * 10)

    for self_data in selves:
        day = self_data.get("day", {})
        energy = day.get("energy", [])
        focus = day.get("focus", [])
        social = day.get("social", [])

        avg_energy = avg(energy)
        avg_focus = avg(focus)
        avg_social = avg(social)
        stability = round((
            _stability(energy) * 0.45 + _stability(focus) * 0.4 + _stability(social) * 0.15
        ), 1)
        recovery = round(max(0.0, min(100.0, sleep * 11 + max(0, 70 - work * 5) + stability * 0.2)), 1)
        burnout_risk = round(max(5.0, min(100.0, burnout_base + (100 - stability) * 0.35 + max(0, 62 - avg_energy) * 0.45)), 1)
        overall = round(avg_energy * 0.34 + avg_focus * 0.38 + avg_social * 0.14 + stability * 0.14, 1)
        focus_window = _peak_window(focus)
        energy_window = _peak_window(energy)
        social_window = _peak_window(social)

        fit_for_deep_work = round(avg_focus * 0.55 + stability * 0.3 + (100 - avg_social) * 0.15, 1)
        fit_for_collab = round(avg_social * 0.45 + avg_energy * 0.35 + bold * 0.2, 1)
        fit_for_creation = round(avg_focus * 0.3 + avg_energy * 0.25 + creative * 0.3 + stability * 0.15, 1)

        enriched.append({
            **self_data,
            "avg_energy": avg_energy,
            "avg_focus": avg_focus,
            "avg_social": avg_social,
            "stability": stability,
            "recovery": recovery,
            "burnout_risk": burnout_risk,
            "overall_score": overall,
            "focus_window": focus_window,
            "energy_window": energy_window,
            "social_window": social_window,
            "fit_for_deep_work": fit_for_deep_work,
            "fit_for_collab": fit_for_collab,
            "fit_for_creation": fit_for_creation,
        })

    if not enriched:
        return {
            "enriched_selves": [],
            "archetype": classify_archetype(profile),
            "coach_summary": "Generate a run to unlock AI insights.",
            "recommendations": [],
            "risks": [],
        }

    best_overall = max(enriched, key=lambda x: x["overall_score"])
    best_focus = max(enriched, key=lambda x: x["fit_for_deep_work"])
    best_social = max(enriched, key=lambda x: x["fit_for_collab"])
    best_creative = max(enriched, key=lambda x: x["fit_for_creation"])
    highest_risk = max(enriched, key=lambda x: x["burnout_risk"])

    readiness_score = round(
        best_overall["overall_score"] * 0.45 + best_overall["recovery"] * 0.25 + best_overall["stability"] * 0.3,
        1,
    )
    archetype = classify_archetype(profile)

    recommendations = [
        f"Use {best_focus['type']} for deep work around {best_focus['focus_window']['label']} when focus is predicted to peak.",
        f"Use {best_social['type']} for collaboration or public-facing tasks, especially near {best_social['social_window']['label']}.",
        f"{best_overall['type']} is the best all-round mode for this profile with a readiness score of {readiness_score:.1f}/100.",
    ]
    if sleep < 7:
        recommendations.append("Raise sleep closer to 7–8 hours to reduce instability and burnout risk across all selves.")
    if work > 8:
        recommendations.append("Current work hours are aggressive; introduce recovery or lighter evening blocks to protect consistency.")
    if creative >= 70:
        recommendations.append("Your profile leans creative; keep one flexible block open each day instead of over-scheduling every hour.")
    if intro >= 70:
        recommendations.append("Batch meetings later in the day and protect the strongest focus window for solo work.")

    risks = []
    if highest_risk["burnout_risk"] >= 65:
        risks.append(f"{highest_risk['type']} shows elevated burnout risk ({highest_risk['burnout_risk']:.1f}/100).")
    if sleep < 6:
        risks.append("Sleep baseline is low, which is likely to weaken recovery and afternoon energy.")
    if work >= 9:
        risks.append("Work/study hours are high enough to create fatigue spillover into the evening timeline.")

    matrix = [
        {"label": "Best overall", "value": best_overall["type"], "score": best_overall["overall_score"]},
        {"label": "Best for deep work", "value": best_focus["type"], "score": best_focus["fit_for_deep_work"]},
        {"label": "Best for collaboration", "value": best_social["type"], "score": best_social["fit_for_collab"]},
        {"label": "Best for creative exploration", "value": best_creative["type"], "score": best_creative["fit_for_creation"]},
    ]

    coach_summary = (
        f"AI coach reads this profile as {archetype.lower()}. {best_overall['type']} is currently the strongest overall mode, "
        f"while the safest deep-work window sits around {best_focus['focus_window']['label']}."
    )

    return {
        "enriched_selves": enriched,
        "best_overall": best_overall,
        "best_focus": best_focus,
        "best_social": best_social,
        "best_creative": best_creative,
        "highest_risk": highest_risk,
        "archetype": archetype,
        "coach_summary": coach_summary,
        "recommendations": recommendations,
        "risks": risks,
        "matrix": matrix,
        "readiness_score": readiness_score,
    }


def dashboard_snapshot(profile_obj: Any, latest_run: Any | None, journal_entries: List[Any]) -> Dict[str, Any]:
    profile = {
        "introversion": getattr(profile_obj, "introversion", 50),
        "boldness": getattr(profile_obj, "boldness", 50),
        "creativity": getattr(profile_obj, "creativity", 50),
        "sleep_hours": getattr(profile_obj, "sleep_hours", 7),
        "work_hours": getattr(profile_obj, "work_hours", 6),
    }
    archetype = classify_archetype(profile)
    journal = journal_intelligence(journal_entries)

    balance_score = round(
        100
        - abs(profile["sleep_hours"] - 7.5) * 10
        - max(0, profile["work_hours"] - 7) * 6
        - abs(profile["introversion"] - profile["boldness"]) * 0.08,
        1,
    )
    balance_score = max(0.0, min(100.0, balance_score))
    recovery_score = round(max(0.0, min(100.0, profile["sleep_hours"] * 11 + (12 - profile["work_hours"]) * 4)), 1)

    latest_analysis = None
    if latest_run is not None:
        latest_analysis = analyze_run(latest_run["profile_snapshot"], latest_run["selves"])

    readiness = latest_analysis["readiness_score"] if latest_analysis else round(balance_score * 0.55 + recovery_score * 0.45, 1)
    burnout_risk = (
        latest_analysis["highest_risk"]["burnout_risk"]
        if latest_analysis and latest_analysis.get("highest_risk")
        else round(max(5.0, min(100.0, max(0, profile["work_hours"] - 7) * 10 + max(0, 6 - profile["sleep_hours"]) * 12)), 1)
    )

    signals = []
    if profile["sleep_hours"] < 7:
        signals.append("Sleep is below the ideal baseline for stable energy.")
    if profile["work_hours"] > 8:
        signals.append("Workload is intense enough to increase fatigue risk.")
    if journal["sentiment_score"] <= 40:
        signals.append("Recent journaling language suggests stress or overload.")
    if not signals:
        signals.append("Current profile is reasonably balanced for experimentation and steady output.")

    next_action = (
        latest_analysis["recommendations"][0]
        if latest_analysis and latest_analysis.get("recommendations")
        else "Generate a simulation to unlock best-self ranking and personalized AI timing windows."
    )

    return {
        "archetype": archetype,
        "journal": journal,
        "balance_score": balance_score,
        "recovery_score": recovery_score,
        "readiness_score": readiness,
        "burnout_risk": burnout_risk,
        "signals": signals,
        "next_action": next_action,
        "latest_analysis": latest_analysis,
    }
