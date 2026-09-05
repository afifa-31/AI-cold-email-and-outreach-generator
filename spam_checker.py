"""
spam_checker.py
----------------
Scans generated email text for common spam-trigger words/phrases that
tend to hurt deliverability (land in Promotions/Spam folders) and gives
the email a simple risk score.
"""

import re

# Common spam trigger words/phrases used by email filters.
# Grouped loosely by category just for readability - the checker treats
# them all the same way.
SPAM_TRIGGER_WORDS = [
    # Urgency / pressure
    "act now", "apply now", "call now", "don't delete", "don't hesitate",
    "urgent", "immediately", "limited time", "act immediately",
    "expires today", "last chance", "time sensitive", "while supplies last",

    # Money / free
    "free", "100% free", "risk-free", "no cost", "no fees", "no obligation",
    "cash bonus", "extra cash", "double your", "earn money", "make money",
    "cheap", "discount", "lowest price", "best price", "save big",
    "billion", "million dollars",

    # Sales / hype
    "guarantee", "guaranteed", "no catch", "no gimmick", "as seen on",
    "amazing", "incredible deal", "once in a lifetime", "miracle",
    "winner", "you've been selected", "congratulations", "click here",
    "click below", "buy now", "order now", "special promotion",

    # Spammy formatting phrases
    "dear friend", "dear valued customer", "undisclosed recipient",
    "this is not spam", "not a scam", "opt in", "unsubscribe now",

    # Finance / loans (common blacklist terms)
    "credit card", "increase sales", "double your income", "work from home",
    "be your own boss", "financial freedom", "no credit check",
    "lower interest rate", "eliminate debt", "consolidate debt",

    # Excessive promises
    "100% satisfied", "satisfaction guaranteed", "no strings attached",
    "why pay more", "bargain", "prize", "gift certificate",
]

# Pre-compile regex patterns (word-boundary, case-insensitive)
_PATTERNS = [
    (phrase, re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE))
    for phrase in SPAM_TRIGGER_WORDS
]


SPAM_WORD_SUGGESTIONS = {
    "act now": "reach out today",
    "apply now": "let me know if you're interested",
    "call now": "feel free to call",
    "don't delete": "worth a look",
    "don't hesitate": "feel free to reply",
    "urgent": "time-sensitive",
    "immediately": "soon",
    "limited time": "for a short while",
    "act immediately": "when you get a chance",
    "expires today": "closes soon",
    "last chance": "final opportunity",
    "time sensitive": "worth prioritizing",
    "while supplies last": "while spots remain",
    "free": "complimentary",
    "100% free": "at no extra cost",
    "risk-free": "no-commitment",
    "no cost": "at no charge",
    "no fees": "without extra charges",
    "no obligation": "no pressure",
    "cash bonus": "added value",
    "extra cash": "added savings",
    "double your": "significantly grow your",
    "earn money": "generate revenue",
    "make money": "drive revenue",
    "cheap": "affordable",
    "discount": "special rate",
    "lowest price": "competitive pricing",
    "best price": "great value",
    "save big": "save significantly",
    "guarantee": "we're confident that",
    "guaranteed": "proven to",
    "no catch": "straightforward",
    "no gimmick": "genuinely",
    "amazing": "notable",
    "incredible deal": "strong offer",
    "once in a lifetime": "rare",
    "miracle": "breakthrough",
    "winner": "top performer",
    "you've been selected": "you came to mind",
    "congratulations": "great news",
    "click here": "see this link",
    "click below": "check the link below",
    "buy now": "get started",
    "order now": "place an order",
    "special promotion": "current offer",
    "dear friend": "hi there",
    "dear valued customer": "hi",
    "this is not spam": "(remove this phrase entirely)",
    "not a scam": "(remove this phrase entirely)",
    "unsubscribe now": "unsubscribe anytime",
    "credit card": "payment details",
    "increase sales": "grow revenue",
    "double your income": "grow your revenue",
    "work from home": "remote-friendly",
    "be your own boss": "run things your way",
    "financial freedom": "financial flexibility",
    "no credit check": "simple approval",
    "lower interest rate": "better rate",
    "eliminate debt": "reduce debt",
    "consolidate debt": "simplify payments",
    "100% satisfied": "confident you'll like it",
    "satisfaction guaranteed": "built to deliver results",
    "no strings attached": "straightforward, no catch",
    "why pay more": "better value",
    "bargain": "good value",
    "prize": "bonus",
    "gift certificate": "voucher",
}


def check_spam_words(text: str):
    """
    Scan `text` for spam trigger words/phrases.

    Returns a dict:
        {
            "matches": [list of matched phrases found],
            "count": int,
            "risk_level": "Low" | "Medium" | "High",
            "excessive_caps": bool,
            "excessive_exclamation": bool,
        }
    """
    if not text:
        return {
            "matches": [],
            "suggestions": {},
            "count": 0,
            "risk_level": "Low",
            "excessive_caps": False,
            "excessive_exclamation": False,
        }

    matches = []
    suggestions = {}
    for phrase, pattern in _PATTERNS:
        if pattern.search(text):
            matches.append(phrase)
            suggestions[phrase] = SPAM_WORD_SUGGESTIONS.get(phrase, "consider rewording")

    count = len(matches)

    # Extra heuristics that hurt deliverability
    exclamation_count = text.count("!")
    excessive_exclamation = exclamation_count >= 3

    # % of fully-uppercase words (ignoring short acronyms like "AI", "CEO")
    words = re.findall(r"[A-Za-z]+", text)
    caps_words = [w for w in words if w.isupper() and len(w) > 3]
    excessive_caps = len(caps_words) >= 3

    # Risk scoring
    score = count + (2 if excessive_exclamation else 0) + (2 if excessive_caps else 0)
    if score == 0:
        risk_level = "Low"
    elif score <= 3:
        risk_level = "Medium"
    else:
        risk_level = "High"

    return {
        "matches": matches,
        "suggestions": suggestions,
        "count": count,
        "risk_level": risk_level,
        "excessive_caps": excessive_caps,
        "excessive_exclamation": excessive_exclamation,
    }
