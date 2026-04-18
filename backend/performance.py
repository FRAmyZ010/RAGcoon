import math
import statistics
from typing import List


def percentile(values: List[float], p: float) -> float:
    """📊 Calculate percentile using linear interpolation."""
    if not values:
        return 0.0

    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * (p / 100)

    lower = math.floor(rank)
    upper = math.ceil(rank)

    if lower == upper:
        return sorted_values[lower]

    weight = rank - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * weight


def format_performance_summary(item_label: str, durations: List[float]) -> str:
    """📈 Return a nicely formatted performance summary."""
    if not durations:
        return _empty_summary(item_label)

    total_time = sum(durations)

    return "\n".join([
        "✨ ================= Performance Summary ================= ✨",
        f"📌 {item_label}: {len(durations)}",
        "----------------------------------------------------------",
        f"⏱️  Total Time : {total_time:.3f}s",
        f"📊 Mean       : {statistics.mean(durations):.3f}s",
        f"📍 Median     : {statistics.median(durations):.3f}s",
        f"🔽 Min        : {min(durations):.3f}s",
        f"🔼 Max        : {max(durations):.3f}s",
        f"🚀 P90        : {percentile(durations, 90):.3f}s",
        f"🔥 P95        : {percentile(durations, 95):.3f}s",
        "==========================================================",
    ])


def _empty_summary(item_label: str) -> str:
    """📭 Return empty performance summary."""
    return "\n".join([
        "✨ ================= Performance Summary ================= ✨",
        f"📌 {item_label}: 0",
        "----------------------------------------------------------",
        "⏱️  Total Time : 0.000s",
        "📊 Mean       : 0.000s",
        "📍 Median     : 0.000s",
        "🔽 Min        : 0.000s",
        "🔼 Max        : 0.000s",
        "🚀 P90        : 0.000s",
        "🔥 P95        : 0.000s",
        "==========================================================",
    ])