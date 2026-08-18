import statistics


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0

    sorted_values = sorted(values)

    k = (len(sorted_values) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)

    if f == c:
        return sorted_values[int(k)]

    return sorted_values[f] + (
        sorted_values[c] - sorted_values[f]
    ) * (k - f)


def format_performance_summary(
    item_label: str,
    durations: list[float],
) -> str:
    if not durations:
        return f"{item_label}: No data"

    total = sum(durations)
    count = len(durations)

    result = (
        f"{item_label}\n"
        f"{'-' * 40}\n"
        f"Count  : {count}\n"
        f"Mean   : {statistics.mean(durations):.3f}s\n"
        f"Median : {statistics.median(durations):.3f}s\n"
        f"Min    : {min(durations):.3f}s\n"
        f"Max    : {max(durations):.3f}s\n"
        f"P90    : {percentile(durations, 90):.3f}s\n"
        f"P95    : {percentile(durations, 95):.3f}s\n"
    )

    if total > 0:
        qps = count / total
        result += f"QPS    : {qps:.2f} req/s\n"

    if count > 1:
        result += (
            f"StdDev : "
            f"{statistics.stdev(durations):.3f}s\n"
        )

    return result