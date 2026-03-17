"""
Saathi — Crisis Detection Module.
Detects crisis/suicide-related keywords in user speech (Hindi, Hinglish, transliterated)
and triggers helpline routing + safety response.

NON-NEGOTIABLE: This module must be active before any public launch.
"""

import re
from dataclasses import dataclass, field

# ─── Helplines ───

HELPLINES = [
    {"name": "Vandrevala Foundation", "number": "1860-2662-345", "available": "24/7"},
    {"name": "iCall", "number": "9152987821", "available": "Mon-Sat, 8am-10pm"},
    {"name": "AASRA", "number": "9820466726", "available": "24/7"},
]

# ─── Crisis Keywords ───
# Organized by severity: critical (immediate danger), high (strong ideation), medium (distress signals)

CRITICAL_KEYWORDS = [
    # Hindi — direct suicide/self-harm
    "आत्महत्या", "ख़ुदकुशी", "खुदकुशी", "फाँसी", "फांसी",
    "ज़हर खा", "जहर खा", "नींद की गोली", "कलाई काट",
    "मरना चाहता", "मरना चाहती", "मर जाना चाहता", "मर जाना चाहती",
    "मर जाऊँ", "मर जाऊं", "मर जाऊ", "मर जाऊंगा", "मर जाऊँगी", "मर जाऊंगी",
    "जान दे दूँ", "जान दे दूं", "जान दे दूंगा", "जान दे दूंगी",
    "suicide कर", "suicide करना",
    # Hinglish / Transliterated
    "aatmahatya", "khudkushi", "khatam kar dunga", "khatam kar dungi",
    "mar jana chahta", "mar jana chahti", "mar jaunga", "mar jaungi",
    "jaan de dunga", "jaan de dungi",
    "suicide", "kill myself", "end my life",
]

HIGH_KEYWORDS = [
    # Hindi — strong ideation / desire to die
    "जीने का मन नहीं", "जीना नहीं चाहता", "जीना नहीं चाहती",
    "ज़िंदगी से तंग", "जिंदगी से तंग", "ज़िंदगी से परेशान", "जिंदगी से परेशान",
    "ज़िंदगी ख़त्म", "जिंदगी खत्म", "सब ख़त्म करना", "सब खत्म करना",
    "कोई फ़ायदा नहीं", "कोई फायदा नहीं", "जीने का कोई मतलब नहीं",
    "मैं बोझ हूँ", "मैं बोझ हूं", "बिना मेरे सब ठीक",
    "कोई मुझे नहीं चाहता", "अकेला मर", "अकेली मर",
    # Hinglish / Transliterated
    "jeene ka mann nahi", "jeena nahi chahta", "jeena nahi chahti",
    "zindagi se tang", "zindagi se pareshan",
    "zindagi khatam", "sab khatam", "koi fayda nahi",
    "i am a burden", "no point in living", "want to die",
    "don't want to live", "better off without me",
]

MEDIUM_KEYWORDS = [
    # Hindi — distress signals (not necessarily suicidal but needs attention)
    "खुद को नुकसान", "खुद को hurt", "self harm",
    "cutting", "कट लगा", "खून निकाल",
    "बहुत तकलीफ़", "बहुत तकलीफ", "बर्दाश्त नहीं हो रहा",
    "सहा नहीं जाता", "पागल हो जाऊँगा", "पागल हो जाऊंगी",
    "रोना बंद नहीं हो रहा", "टूट गया हूँ", "टूट गई हूँ",
    # Hinglish
    "self harm", "hurt myself", "khud ko nuksan",
    "bardaasht nahi", "saha nahi jaata", "toot gaya",
]


@dataclass
class CrisisResult:
    """Result of crisis keyword detection."""
    is_crisis: bool = False
    severity: str = "none"            # "none", "medium", "high", "critical"
    matched_keywords: list[str] = field(default_factory=list)
    helplines: list[dict] = field(default_factory=list)
    response_text_hindi: str = ""
    response_text_english: str = ""


def detect_crisis(text: str) -> CrisisResult:
    """
    Scan user text for crisis/suicide-related keywords.

    Args:
        text: The STT-transcribed user speech (Hindi/Hinglish/English).

    Returns:
        CrisisResult with severity level and matched keywords.
    """
    if not text:
        return CrisisResult()

    text_lower = text.lower().strip()
    matched = []
    severity = "none"

    # Check critical keywords first (highest priority)
    for keyword in CRITICAL_KEYWORDS:
        if keyword.lower() in text_lower:
            matched.append(keyword)
            severity = "critical"

    # Check high keywords
    if severity != "critical":
        for keyword in HIGH_KEYWORDS:
            if keyword.lower() in text_lower:
                matched.append(keyword)
                if severity != "critical":
                    severity = "high"

    # Check medium keywords
    if severity == "none":
        for keyword in MEDIUM_KEYWORDS:
            if keyword.lower() in text_lower:
                matched.append(keyword)
                severity = "medium"

    if not matched:
        return CrisisResult()

    # Build response based on severity
    if severity == "critical":
        response_hindi = (
            "मैं समझ रहा हूँ कि तुम बहुत मुश्किल में हो। "
            "तुम अकेले नहीं हो। अभी Vandrevala Foundation helpline पर call करो, "
            "नंबर है 1860-2662-345। वो चौबीसों घंटे available हैं और ज़रूर मदद करेंगे।"
        )
        response_english = (
            "I can see you're going through a very difficult time. "
            "You are not alone. Please call the Vandrevala Foundation helpline now "
            "at 1860-2662-345. They are available 24/7 and will help."
        )
    elif severity == "high":
        response_hindi = (
            "मुझे तुम्हारी बहुत चिंता हो रही है। "
            "कभी कभी बात करने से बहुत फ़र्क पड़ता है। "
            "क्या तुम iCall helpline पर बात करोगे? नंबर है 9152987821। "
            "वो trained counselors हैं और तुम्हारी मदद कर सकते हैं।"
        )
        response_english = (
            "I'm really concerned about you. "
            "Sometimes talking to someone can make a big difference. "
            "Would you consider calling iCall at 9152987821? "
            "They have trained counselors who can help."
        )
    else:  # medium
        response_hindi = (
            "लगता है तुम बहुत परेशान हो। मैं तुम्हारे साथ हूँ। "
            "अगर कभी लगे कि बहुत ज़्यादा हो रहा है, तो professional से बात करना बहुत अच्छा रहेगा। "
            "Vandrevala Foundation का नंबर है 1860-2662-345।"
        )
        response_english = (
            "It seems like you're going through a really tough time. I'm here with you. "
            "If it ever feels like too much, talking to a professional can really help. "
            "The Vandrevala Foundation number is 1860-2662-345."
        )

    return CrisisResult(
        is_crisis=True,
        severity=severity,
        matched_keywords=matched,
        helplines=HELPLINES,
        response_text_hindi=response_hindi,
        response_text_english=response_english,
    )


def anonymize_trigger_text(text: str, max_length: int = 100) -> str:
    """
    Anonymize trigger text for logging — keep only the relevant portion
    and truncate to avoid storing full conversations.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
