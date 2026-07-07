from datetime import date, timedelta
from typing import Tuple


def compute_sm2(
    interval: int,
    ease_factor: float,
    quality: int,
) -> Tuple[int, float, date]:
    """
    SM-2 Spaced Repetition Algorithm (SuperMemo 2).
    quality: 0-5  (0=complete blackout, 5=perfect response)
    Returns: (new_interval_days, new_ease_factor, next_review_date)
    """
    if quality < 0 or quality > 5:
        raise ValueError("quality must be between 0 and 5 inclusive")

    if quality >= 3:
        if interval <= 1:
            new_interval = 1
        elif interval <= 6:
            new_interval = 6
        else:
            new_interval = round(interval * ease_factor)
    else:
        new_interval = 1

    new_ease = ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ease = round(max(1.3, new_ease), 4)

    next_review = date.today() + timedelta(days=new_interval)
    return new_interval, new_ease, next_review
