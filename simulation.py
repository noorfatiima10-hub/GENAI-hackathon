import math
import random
from dataclasses import asdict, dataclass
from typing import Dict, List


@dataclass
class Profile:
    introversion: int
    boldness: int
    creativity: int
    sleep_hours: int
    work_hours: int


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _circadian_base(hour: int) -> float:
    t = (hour / 24.0) * 2 * math.pi
    return 0.55 + 0.25 * math.sin(t - 1.0) + 0.10 * math.sin(2 * t + 0.5)


def _sleep_penalty(profile: Profile) -> float:
    ideal = 7.5
    diff = abs(profile.sleep_hours - ideal)
    return clamp(1.0 - 0.08 * diff, 0.55, 1.0)


def _trait_modifier(profile: Profile, kind: str) -> Dict[str, float]:
    intro = profile.introversion / 100.0
    bold = profile.boldness / 100.0
    creat = profile.creativity / 100.0

    if kind == "Base Self":
        return {"energy": 1.0, "focus": 1.0, "social": 1.0}
    if kind == "Bold Self":
        return {"energy": 1.05 + 0.10 * bold, "focus": 1.02, "social": 1.14}
    if kind == "Introverted Self":
        return {"energy": 0.98, "focus": 1.05 + 0.10 * intro, "social": 0.80}
    if kind == "Creative Self":
        return {"energy": 1.00, "focus": 0.95 + 0.15 * creat, "social": 1.0}
    return {"energy": 1.0, "focus": 1.0, "social": 1.0}


def _split_block(label: str, start: int, end: int, intensity: float) -> List[Dict]:
    start = int(clamp(start, 0, 24))
    end = int(clamp(end, 0, 24))
    if start == end:
        return []
    if start < end:
        return [{"label": label, "start": start, "end": end, "intensity": intensity}]
    return [
        {"label": label, "start": start, "end": 24, "intensity": intensity},
        {"label": label, "start": 0, "end": end, "intensity": intensity},
    ]


def _daily_schedule(profile: Profile, kind: str) -> List[Dict]:
    work = clamp(profile.work_hours, 0, 12)
    sleep = clamp(profile.sleep_hours, 4, 10)

    # Keeps bedtime around 23:00 and moves wake time according to sleep hours.
    bedtime = 23
    wake = int(clamp(bedtime + sleep - 24, 5, 9))
    morning_end = min(wake + 2, 11)
    work_start = morning_end
    work_end = min(work_start + int(work), 18)
    evening_start = min(work_end + 1, 19)

    blocks: List[Dict] = []
    blocks.extend(_split_block("Sleep", 0, wake, 0.10))
    blocks.extend(_split_block("Morning Routine", wake, morning_end, 0.35))

    if work > 0:
        blocks.extend(_split_block("Deep Work / Study", work_start, work_end, 0.88))
        if work_end < evening_start:
            blocks.extend(_split_block("Break / Meals", work_end, evening_start, 0.32))
    else:
        blocks.extend(_split_block("Personal Tasks", work_start, evening_start, 0.50))

    if kind == "Bold Self":
        blocks.extend(_split_block("Networking / Public Tasks", evening_start, 20, 0.70))
    elif kind == "Introverted Self":
        blocks.extend(_split_block("Solo Recharge", evening_start, 20, 0.42))
    elif kind == "Creative Self":
        blocks.extend(_split_block("Creative Flow", evening_start, 20, 0.76))
    else:
        blocks.extend(_split_block("Family / Relax", evening_start, 20, 0.55))

    blocks.extend(_split_block("Recovery / Reflection", 20, 22, 0.28))
    blocks.extend(_split_block("Wind Down", 22, bedtime, 0.20))

    return [b for b in blocks if b["end"] > b["start"]]


def simulate_day(profile: Profile, kind: str, seed: int) -> Dict:
    rnd = random.Random(seed)
    mod = _trait_modifier(profile, kind)
    sleep_mult = _sleep_penalty(profile)

    energy, focus, social = [], [], []
    for h in range(24):
        base = _circadian_base(h) * sleep_mult
        noise = rnd.uniform(-0.07, 0.07)

        e = clamp((base + noise) * mod["energy"], 0.15, 1.0)
        f = clamp((base + rnd.uniform(-0.06, 0.06)) * mod["focus"], 0.10, 1.0)
        s = clamp(
            (0.45 + 0.20 * math.sin(((h - 14) / 24) * 2 * math.pi) + rnd.uniform(-0.05, 0.05)) * mod["social"],
            0.05,
            1.0,
        )

        if kind == "Introverted Self" and 8 <= h <= 14:
            f = clamp(f + 0.04, 0.10, 1.0)
        if kind == "Creative Self" and 15 <= h <= 20:
            e = clamp(e + 0.03, 0.15, 1.0)
            f = clamp(f + 0.02, 0.10, 1.0)
        if kind == "Bold Self" and 16 <= h <= 21:
            s = clamp(s + 0.05, 0.05, 1.0)

        energy.append(round(e * 100))
        focus.append(round(f * 100))
        social.append(round(s * 100))

    blocks = _daily_schedule(profile, kind)
    return {"energy": energy, "focus": focus, "social": social, "blocks": blocks}


def simulate_week(profile: Profile, kind: str, seed: int) -> Dict:
    days = [simulate_day(profile, kind, seed + d * 101) for d in range(7)]
    hourly_avg_energy = [round(sum(day["energy"][h] for day in days) / 7) for h in range(24)]
    return {"days": days, "hourly_avg_energy": hourly_avg_energy}


def generate_parallel_selves(profile: Profile, seed: int = 42) -> List[Dict]:
    kinds = ["Base Self", "Bold Self", "Introverted Self", "Creative Self"]
    out = []
    for i, kind in enumerate(kinds):
        day = simulate_day(profile, kind, seed + i * 17)
        week = simulate_week(profile, kind, seed + i * 17)
        out.append({"type": kind, "day": day, "week": week})
    return out


def profile_to_dict(profile: Profile) -> Dict:
    return asdict(profile)
