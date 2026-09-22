"""Professional look: har style ke liye transitions ka pool aur colour grading."""
import random

SIMPLE = "fade"  # sab se safe transition (fallback)

# ffmpeg xfade ke naam. Har style ka apna mizaj
POOLS: dict[str, list[str]] = {
    "modern-tech": ["smoothleft", "slideup", "circleopen", "zoomin", "radial", "smoothright", "hlslice", "fadewhite"],
    "cinematic": ["fadeblack", "dissolve", "fadewhite", "smoothup", "fade", "circleclose"],
    "documentary": ["fade", "dissolve", "smoothleft", "fadegrays", "smoothright"],
    "minimal": ["fade", "dissolve", "smoothleft"],
}

# Halka colour grade: alag alag clips ek jaise dikhte hain (cohesive, "edited" look)
GRADE: dict[str, str] = {
    "modern-tech": "eq=contrast=1.08:saturation=1.15",
    "cinematic": "eq=contrast=1.10:saturation=0.95,colorbalance=rs=0.04:bs=-0.04:rh=0.05:bh=-0.03",
    "documentary": "eq=contrast=1.04:saturation=1.02",
    "minimal": "eq=contrast=1.02:saturation=0.96",
}


# Vignette (kinare halke gehre) sundar hai lekin CPU-bhaari: sirf "balanced" speed mein
VIGNETTE: dict[str, str] = {"modern-tech": "vignette=PI/6", "cinematic": "vignette=PI/4"}


def pick_transitions(style: str, n: int, seed: str) -> list[str]:
    """Index i = scene i mein aane wali transition (0 unused). Lagatar do baar ek jaisi nahi, seed se har video alag."""
    pool = list(POOLS.get(style, POOLS["modern-tech"]))
    random.Random(seed).shuffle(pool)
    out = [SIMPLE]
    for i in range(1, n):
        name = pool[(i - 1) % len(pool)]
        if name == out[-1] and len(pool) > 1:
            name = pool[i % len(pool)]
        out.append(name)
    return out


def grade_filter(style: str, total: float, vignette: bool = False) -> str:
    """Colour grade (+ optional vignette) + shuruaat mein halka fade-in aur aakhir mein fade-out."""
    g = GRADE.get(style, GRADE["modern-tech"])
    if vignette and style in VIGNETTE:
        g += "," + VIGNETTE[style]
    return f"{g},fade=t=in:st=0:d=0.35,fade=t=out:st={max(0.0, total - 0.5):.3f}:d=0.5"
