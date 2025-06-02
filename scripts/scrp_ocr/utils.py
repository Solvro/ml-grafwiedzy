import math
from typing import Tuple

def calculate_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """
    Calculate the Euclidean distance between two points.

    Args:
        p1 (Tuple[float, float]): First point as (x, y).
        p2 (Tuple[float, float]): Second point as (x, y).

    Returns:
        float: Euclidean distance between p1 and p2.
    """
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])
