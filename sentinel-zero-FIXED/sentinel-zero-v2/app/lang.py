"""Keyword rules for English, Hindi and Odia community reports.

The keyword lists were drafted by the team. They must be checked by native speakers
before any real use (see docs/limitations.md).
"""
import re

KEYWORDS = {
    "water_odour": ["smell", "smells", "odour", "odor", "stink", "stinks",
                    "बदबू", "गंध", "ଦୁର୍ଗନ୍ଧ"],
    "water_colour": ["colour", "color", "yellow", "brown", "muddy",
                     "पीला", "भूरा", "ରଙ୍ଗ", "ହଳଦିଆ"],
    "diarrhoea_symptoms": ["diarrhoea", "diarrhea", "loose motion", "loose motions", "vomit", "vomiting",
                           "दस्त", "उल्टी", "ଝାଡ଼ା", "ଝାଡା"],
}
ORDER = ("water_odour", "water_colour", "diarrhoea_symptoms")

_ASCII_NEGATION = re.compile(r"\b(no|not|clear|normal|fine|without)\b")
_OTHER_NEGATION = ("नहीं", "साफ", "ନାହିଁ", "ସଫା")


def classify(text: str) -> str:
    """Return a report category from keywords in English, Hindi or Odia, or 'other'."""
    lower = text.lower()
    for category in ORDER:
        if any(keyword in lower for keyword in KEYWORDS[category]):
            return category
    return "other"


def has_negation(text: str) -> bool:
    """True when the report says the water is clear, normal or absent of a problem."""
    lower = text.lower()
    return bool(_ASCII_NEGATION.search(lower)) or any(word in text for word in _OTHER_NEGATION)
