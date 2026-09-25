"""Small, cited starter set for companion-crop suggestions.

These are planning prompts rather than yield predictions. Spacing, planting
dates, varieties, water, and local pest pressure determine whether a pairing
works on a particular farm.
"""

from suitability import evaluate


COMPANION_SYSTEMS = [
    {
        "crops": ("Corn (Maize)", "Green Bean", "Pumpkin"),
        "name": "Three-crop maize, bean, and squash plan",
        "why": (
            "A tall crop, a climbing legume, and a spreading ground crop can use "
            "different parts of the field. This traditional combination still needs "
            "locally adapted spacing and planting dates."
        ),
        "manage": (
            "Use a sturdy maize variety and allow enough light and space for the "
            "bean and squash. Watch water competition during dry periods."
        ),
        "source": "https://www.fao.org/4/a0218e/A0218E16.htm",
    },
    {
        "crops": ("Corn (Maize)", "Green Bean"),
        "name": "Maize with green bean",
        "why": (
            "The crops can use different canopy and root spaces; pole beans may "
            "climb maize where the variety and planting arrangement suit the farm."
        ),
        "manage": (
            "Stagger planting if needed to reduce early competition. Legume nitrogen "
            "benefits build over time and should not be treated as an instant fertilizer."
        ),
        "source": "https://extension.oregonstate.edu/imported-publication/companion-planting",
    },
    {
        "crops": ("Cabbage", "Green Bean"),
        "name": "Cabbage with a legume",
        "why": (
            "Extension guidance lists legumes as a possible companion for brassicas; "
            "plant residues can contribute nitrogen as they decompose."
        ),
        "manage": (
            "Keep rows far enough apart for airflow and field access. Count on soil "
            "testing, not the pairing alone, to guide nutrient decisions."
        ),
        "source": "https://extension.oregonstate.edu/imported-publication/companion-planting",
    },
    {
        "crops": ("Broccoli", "Green Bean"),
        "name": "Broccoli with a legume",
        "why": (
            "A legume can diversify a brassica planting and may contribute nitrogen "
            "after its roots and residues decompose."
        ),
        "manage": (
            "Leave enough room for the mature broccoli canopy and check local planting "
            "dates so both crops establish well."
        ),
        "source": "https://extension.oregonstate.edu/imported-publication/companion-planting",
    },
    {
        "crops": ("Carrot", "Tomato"),
        "name": "Carrot near tomato",
        "why": (
            "Tomato foliage can provide some shade for cool-season carrots in a garden "
            "setting, while the crops occupy different canopy layers."
        ),
        "manage": (
            "Avoid letting mature tomato plants shade carrots too heavily; harvest and "
            "water needs may differ."
        ),
        "source": "https://extension.oregonstate.edu/imported-publication/companion-planting",
    },
]


def recommendations(main_crop: str, climate: dict, soil: dict) -> list[dict]:
    """Return cited pairings whose companion crop also screens for this site."""
    from crop_data import CROP_THRESHOLDS

    results = []
    seen = set()
    for system in COMPANION_SYSTEMS:
        if main_crop not in system["crops"]:
            continue
        for companion in system["crops"]:
            if companion == main_crop or companion in seen:
                continue
            seen.add(companion)
            thresholds = CROP_THRESHOLDS.get(companion)
            if not thresholds:
                continue
            verdict, score, reasons = evaluate(climate, soil, thresholds)
            results.append(
                {
                    "crop": companion,
                    "system": system["name"],
                    "why": system["why"],
                    "manage": system["manage"],
                    "source": system["source"],
                    "verdict": verdict,
                    "score": score,
                    "reasons": reasons,
                }
            )
    results.sort(key=lambda item: item["score"] if item["score"] is not None else -1, reverse=True)
    return results
