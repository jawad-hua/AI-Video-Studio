MAX_TOTAL = 60.0  # hard limit: video 60 sec se lambi kabhi nahi
MIN_SCENE = 2.0   # koi scene 2 sec se chhota nahi


def normalize_durations(durations: list[float], target: float) -> list[float]:
    """Total duration kabhi min(target, 60) se zyada nahi hogi.

    - total <= target ho to durations waise hi rehti hain (sirf sahi round hoti hain)
    - total > target ho to sab scenes proportion mein compress hote hain
    Andar tenths (0.1 sec) ke integers use hote hain taake float error na aaye.
    """
    if not durations:
        return []

    target_t = int(round(min(target, MAX_TOTAL) * 10))
    min_t = int(MIN_SCENE * 10)
    d = [max(min_t, int(round(float(x) * 10))) for x in durations]
    n = len(d)

    if sum(d) <= target_t:
        return [x / 10 for x in d]

    # Target itna chhota ho ke MIN_SCENE bhi na aaye: sabko barabar baant do
    if target_t <= n * min_t:
        base = target_t // n
        out = [base] * n
        for i in range(target_t - base * n):
            out[i] += 1
        return [x / 10 for x in out]

    # MIN_SCENE se upar ka hissa proportion mein kam karo
    extras = [x - min_t for x in d]
    budget = target_t - n * min_t
    scale = budget / sum(extras)
    out = [min_t + int(e * scale) for e in extras]

    # Floor karne se jo tenths bach gaye, sabse lambe scenes ko do
    remaining = target_t - sum(out)
    order = sorted(range(n), key=lambda i: -d[i])
    for k in range(remaining):
        out[order[k % n]] += 1
    return [x / 10 for x in out]
