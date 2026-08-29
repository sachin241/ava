"""Deterministic semantic danger classification for verified observations.

The classifier produces facts only.  It never speaks and does not make the
final safety decision; those responsibilities remain with SafetyEngine and
ResponseManager.
"""
from __future__ import annotations

import re
import time
from typing import Any


UNKNOWN_HAZARD = "UNKNOWN_HAZARD"

# Public vocabulary kept intentionally small and stable for API consumers.
DANGER_TAXONOMY = {
    "PHYSICAL": {"OBSTACLE", "COLLISION_HAZARD", "STAIR_HAZARD", "DEBRIS", "BARRIER", "FLOOR_OBSTACLE"},
    "ROAD": {"ROAD_HAZARD", "ROAD_WORK", "ROAD_CLOSURE", "TRAFFIC_HAZARD", "PEDESTRIAN_CROSSING", "STOP_SIGNAL", "TRAFFIC_SIGNAL"},
    "FLOOR": {"WET_FLOOR", "SLIPPERY_FLOOR", "UNEVEN_SURFACE", "OPENING_HOLE", "STAIR_HAZARD"},
    "WARNING": {"GENERAL_WARNING", "ELECTRICAL_HAZARD", "FIRE_HAZARD", "NO_ENTRY", "RESTRICTED_AREA", "CONSTRUCTION", "DANGER", "EMERGENCY_EXIT"},
    "EMERGENCY": {"EMERGENCY", "SOS", "FIRE", "EVACUATION"},
}

_OBJECT_RULES = {
    "stairs": ("PHYSICAL", "STAIR_HAZARD", "high"),
    "stair": ("PHYSICAL", "STAIR_HAZARD", "high"),
    "fire": ("EMERGENCY", "FIRE", "critical"),
    "smoke": ("EMERGENCY", "FIRE", "critical"),
    "barrier": ("PHYSICAL", "BARRIER", "high"),
    "debris": ("PHYSICAL", "DEBRIS", "medium"),
    "chair": ("PHYSICAL", "OBSTACLE", "medium"),
    "table": ("PHYSICAL", "OBSTACLE", "medium"),
    "bench": ("PHYSICAL", "OBSTACLE", "medium"),
    "bicycle": ("PHYSICAL", "FLOOR_OBSTACLE", "medium"),
    "car": ("ROAD", "TRAFFIC_HAZARD", "high"),
    "truck": ("ROAD", "TRAFFIC_HAZARD", "high"),
    "bus": ("ROAD", "TRAFFIC_HAZARD", "high"),
    "person": ("ROAD", "PEDESTRIAN_CROSSING", "medium"),
}

_TEXT_RULES = (
    (re.compile(r"\bwet\s+floor\b", re.I), "FLOOR", "WET_FLOOR", "high"),
    (re.compile(r"\bslippery\b", re.I), "FLOOR", "SLIPPERY_FLOOR", "high"),
    (re.compile(r"\buneven\s+(surface|floor)\b", re.I), "FLOOR", "UNEVEN_SURFACE", "medium"),
    (re.compile(r"\b(open|floor)\s*(hole|opening)|\bhole\b", re.I), "FLOOR", "OPENING_HOLE", "critical"),
    (re.compile(r"\bhigh\s+voltage\b", re.I), "WARNING", "ELECTRICAL_HAZARD", "critical"),
    (re.compile(r"\bfire\s+hazard\b|\bflammable\b", re.I), "WARNING", "FIRE_HAZARD", "critical"),
    (re.compile(r"\broad\s+work\b|\broadworks\b", re.I), "ROAD", "ROAD_WORK", "high"),
    (re.compile(r"\broad\s+closed?\b|\broad\s+closure\b", re.I), "ROAD", "ROAD_CLOSURE", "high"),
    (re.compile(r"\bno\s+entry\b", re.I), "WARNING", "NO_ENTRY", "high"),
    (re.compile(r"\bdo\s+not\s+enter\b", re.I), "WARNING", "NO_ENTRY", "high"),
    (re.compile(r"\brestricted\s+area\b", re.I), "WARNING", "RESTRICTED_AREA", "high"),
    (re.compile(r"\bconstruction\b", re.I), "WARNING", "CONSTRUCTION", "medium"),
    (re.compile(r"\bemergency\s+exit\b", re.I), "WARNING", "EMERGENCY_EXIT", "low"),
    (re.compile(r"\bfire\s+exit\b", re.I), "EMERGENCY", "EVACUATION", "high"),
    (re.compile(r"\b(stop|danger|warning)\s+sign\b|\bdanger\b", re.I), "WARNING", "DANGER", "high"),
)

_SYMBOL_RULES = {
    "⚡": ("WARNING", "ELECTRICAL_HAZARD", "critical"),
    "🔥": ("WARNING", "FIRE_HAZARD", "critical"),
    "⚠": ("WARNING", "GENERAL_WARNING", "high"),
    "🚫": ("WARNING", "NO_ENTRY", "high"),
    "⛔": ("WARNING", "NO_ENTRY", "high"),
}


def normalize_sign_text(text: str) -> str:
    """Conservative OCR normalization: spacing/case/punctuation only."""
    value = str(text or "").replace("\x0c", " ")
    value = re.sub(r"[^\w\s']", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip().upper()


def _danger(category: str, danger_type: str, confidence: float, *, direction: str | None = None,
            proximity: str | None = None, severity: str = "medium", source: list[str] | None = None,
            timestamp: int | None = None, danger_id: str | None = None,
            observation: str = "object") -> dict[str, Any]:
    return {
        "danger_id": danger_id or f"{danger_type.lower()}-{timestamp or int(time.time() * 1000)}",
        "category": category,
        "type": danger_type,
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
        "direction": direction,
        "proximity": proximity,
        "severity": severity,
        "source": source or [],
        "observation": observation,
        "active": True,
        "timestamp": timestamp or int(time.time() * 1000),
    }


def classify_detections(objects: list[dict[str, Any]], timestamp: int | None = None) -> list[dict[str, Any]]:
    """Classify tracked objects while preserving detection confidence separately."""
    results: list[dict[str, Any]] = []
    for obj in objects:
        label = str(obj.get("name", "")).lower().strip()
        rule = _OBJECT_RULES.get(label)
        if rule is None:
            continue
        category, danger_type, severity = rule
        confidence = float(obj.get("confidence", 0.0))
        if danger_type == "OBSTACLE" and obj.get("motion") == "approaching":
            danger_type, severity = "COLLISION_HAZARD", "critical"
            confidence = min(1.0, confidence + 0.05)
        results.append(_danger(category, danger_type, confidence,
                               direction=obj.get("direction"), proximity=obj.get("proximity"),
                               severity=severity, source=["yolo", label], timestamp=timestamp,
                               danger_id=f"{danger_type.lower()}-{obj.get('id', label)}"))
    return results


def classify_text(text: str, confidence: float = 1.0, timestamp: int | None = None) -> list[dict[str, Any]]:
    """Classify OCR text conservatively; unknown warning language stays unknown."""
    clean = normalize_sign_text(text)
    # OCR adapters commonly report percentages (0-100), while the danger
    # contract uses normalized confidence (0-1).
    if confidence > 1:
        confidence = confidence / 100.0
    if not clean:
        return []
    results = []
    for pattern, category, danger_type, severity in _TEXT_RULES:
        if pattern.search(clean):
            results.append(_danger(category, danger_type, confidence, severity=severity,
                                   source=["ocr", clean[:120]], timestamp=timestamp,
                                   danger_id=f"{danger_type.lower()}-ocr", observation="danger_board"))
    if not results and re.search(r"\b(warning|caution|hazard|danger)\b", clean, re.I):
        results.append(_danger("WARNING", UNKNOWN_HAZARD, min(confidence, 0.65), severity="medium",
                               source=["ocr", clean[:120]], timestamp=timestamp, danger_id="unknown-ocr", observation="danger_board"))
    return results


def classify_sign(text: str = "", symbols: list[str] | None = None, confidence: float = 1.0,
                  timestamp: int | None = None) -> list[dict[str, Any]]:
    """Classify a visible board/sign from OCR and a controlled symbol set.

    Matching OCR and symbol evidence is fused into one danger object rather
    than producing duplicate alerts. Unknown ordinary text yields no danger.
    """
    text_dangers = classify_text(text, confidence, timestamp)
    symbol_dangers: list[dict[str, Any]] = []
    for symbol in symbols or []:
        rule = _SYMBOL_RULES.get(symbol)
        if not rule:
            continue
        category, danger_type, severity = rule
        symbol_dangers.append(_danger(category, danger_type, confidence, severity=severity,
                                      source=["symbol", symbol], timestamp=timestamp,
                                      danger_id=f"{danger_type.lower()}-symbol", observation="danger_symbol"))
    fused = {danger["type"]: danger for danger in text_dangers}
    for danger in symbol_dangers:
        existing = fused.get(danger["type"])
        if existing:
            existing["confidence"] = round(min(1.0, max(existing["confidence"], danger["confidence"]) + 0.1), 4)
            existing["source"] = list(dict.fromkeys(existing["source"] + danger["source"]))
        else:
            fused[danger["type"]] = danger
    return list(fused.values())


def explain_dangers(dangers: list[dict[str, Any]]) -> str:
    if not dangers:
        return "No specific danger sign was identified."
    labels = ", ".join(d["type"].replace("_", " ").lower() for d in dangers[:3])
    return f"This sign indicates {labels}."


def classify(objects: list[dict[str, Any]] | None = None, text: str | None = None,
             timestamp: int | None = None) -> list[dict[str, Any]]:
    return classify_detections(objects or [], timestamp) + classify_sign(text or "", timestamp=timestamp)
