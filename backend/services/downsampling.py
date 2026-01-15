"""
Analytics Downsampling Service

Provides downsampling algorithms for analytics data visualization:
- LTTB (Largest Triangle Three Buckets) for shape-preserving downsampling
- Smart downsampling that preserves critical events
- Uniform sampling for general use
- Duration formatting utilities
"""

from typing import List, Dict


def format_duration_hms(seconds: float) -> str:
    """
    Format duration in seconds as HH:MM:SS.

    Args:
        seconds: Duration in seconds (float or int)

    Returns:
        Formatted string "HH:MM:SS"

    Examples:
        >>> format_duration_hms(3661.5)
        '01:01:01'
        >>> format_duration_hms(90)
        '00:01:30'
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def lttb_downsample(data: List[Dict], max_points: int, x_key: str = 'timestamp', y_key: str = 'value') -> List[Dict]:
    """
    Largest Triangle Three Buckets (LTTB) downsampling algorithm.
    Preserves visual shape by selecting points that form largest triangles.

    Args:
        data: List of dicts with x (timestamp) and y (value) keys
        max_points: Target number of points
        x_key: Key for x-axis value (timestamp)
        y_key: Key for y-axis value

    Returns:
        Downsampled list with ~max_points entries
    """
    if len(data) <= max_points:
        return data

    # Always include first and last points
    sampled = [data[0]]
    bucket_size = (len(data) - 2) / (max_points - 2)

    a = 0  # Initially the first point
    for i in range(max_points - 2):
        # Calculate bucket range
        avg_range_start = int((i + 1) * bucket_size) + 1
        avg_range_end = int((i + 2) * bucket_size) + 1
        avg_range_end = min(avg_range_end, len(data))

        # Calculate average point in next bucket
        avg_x = sum(d[x_key] for d in data[avg_range_start:avg_range_end]) / (avg_range_end - avg_range_start)
        avg_y = sum(d[y_key] for d in data[avg_range_start:avg_range_end]) / (avg_range_end - avg_range_start)

        # Find point in current bucket that forms largest triangle
        range_start = int(i * bucket_size) + 1
        range_end = int((i + 1) * bucket_size) + 1

        max_area = -1
        max_area_point = None

        point_a_x = data[a][x_key]
        point_a_y = data[a][y_key]

        for j in range(range_start, range_end):
            # Calculate triangle area
            point_b_x = data[j][x_key]
            point_b_y = data[j][y_key]
            area = abs((point_a_x - avg_x) * (point_b_y - point_a_y) -
                      (point_a_x - point_b_x) * (avg_y - point_a_y))

            if area > max_area:
                max_area = area
                max_area_point = j

        sampled.append(data[max_area_point])
        a = max_area_point

    sampled.append(data[-1])  # Always include last point
    return sampled


def smart_downsample_delta_t(events: List[Dict], max_points: int, critical_threshold: float = 1.5) -> List[Dict]:
    """
    Smart downsampling for Δt events: preserves all critical events + LTTB on rest.

    Args:
        events: List of delta_t event dicts with 'delta_t' and 'timestamp' keys
        max_points: Target number of points
        critical_threshold: |Δt| threshold for critical events (default 1.5s)

    Returns:
        Downsampled list with all critical events + LTTB sampled normal events
    """
    if len(events) <= max_points:
        return events

    # Separate critical and normal events
    critical = [e for e in events if abs(e['delta_t']) >= critical_threshold]
    normal = [e for e in events if abs(e['delta_t']) < critical_threshold]

    # If critical events alone exceed max_points, return all critical (rare case)
    if len(critical) >= max_points:
        return sorted(critical, key=lambda e: e['timestamp'])

    # Apply LTTB to normal events for remaining budget
    remaining_budget = max_points - len(critical)
    sampled_normal = lttb_downsample(normal, remaining_budget, x_key='timestamp', y_key='delta_t')

    # Merge and sort by timestamp
    result = critical + sampled_normal
    return sorted(result, key=lambda e: e['timestamp'])


def sample_events(events: list, max_points: int) -> list:
    """
    Uniform sampling for ANY event type.
    Takes 1 event every N to reach max_points.

    Args:
        events: List of events (any type)
        max_points: Target number of points (e.g., 500)

    Returns:
        Sampled events list (or original if already below max_points)
    """
    if len(events) <= max_points:
        return events  # No sampling needed

    step = len(events) / max_points
    sampled = []
    for i in range(max_points):
        idx = int(i * step)
        sampled.append(events[idx])

    return sampled
