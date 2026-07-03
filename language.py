"""
language.py
------------
Code-side Spanish/English detector for outbound delivery emails.

Why this exists: coi_system_prompt.txt's OUTPUT FORMAT does not carry a
language field for delivery purposes (see prompt line ~436 — the standard
COI delivery cover note is English-only by design, regardless of the
insured's language). Alex's rule overrides that default for the *complete
Spanish request* case: those must get a Spanish delivery email with the COI
attached. Since the parsed JSON has no reply-language signal for send_pdf /
complex-review paths, this module detects language directly off the raw
client email (subject + body).

Precision over recall: default to English when unsure. A Spanish email
mistakenly sent in English is a minor style miss; an English-speaking
client's request answered in Spanish is a much worse experience. So the
detector requires reasonably strong signal before flipping to Spanish.
"""

import re

# Strong Spanish markers: whole words/phrases unlikely to appear in an
# English email by accident. Matched case-insensitively on word boundaries.
_SPANISH_MARKERS = [
    r"\bnecesito\b",
    r"\bpor favor\b",
    r"\badjunto\b",
    r"\badjunta\b",
    r"\bseguro\b",
    r"\bseguros\b",
    r"\bcertificado\b",
    r"\bgracias\b",
    r"\bbuenos d[ií]as\b",
    r"\bbuenas tardes\b",
    r"\bbuenas noches\b",
    r"\bhola\b",
    r"\bpara\b",
    r"\bdirecci[oó]n\b",
    r"\benv[ií]ame\b",
    r"\benv[ií]eme\b",
    r"\bm[aá]ndame\b",
    r"\bpodr[ií]a\b",
    r"\bfavor de\b",
    r"\bpor medio de\b",
    r"\bsaludos\b",
    r"\bcordialmente\b",
    r"\bcuanto antes\b",
    r"\btitular\b",
    r"\basegurado\b",
    r"\bp[oó]liza\b",
    r"\bcompa(?:ñía|ñia|nía)\b",
    r"\bnuevo trabajo\b",
    r"\bnueva direcci[oó]n\b",
]

_SPANISH_MARKER_RE = re.compile("|".join(_SPANISH_MARKERS), re.IGNORECASE)

# Spanish-only accented characters / punctuation. Their mere presence in
# reasonable density is itself a signal (English business email rarely
# contains ñ, inverted punctuation, or accented vowels at all).
_SPANISH_CHAR_RE = re.compile(r"[ñÑ¿¡áéíóúÁÉÍÓÚ]")

# Minimum combined text length before we trust the detector at all. Very
# short bodies ("thanks!", "ok") don't carry enough signal either way.
_MIN_LEN_FOR_DETECTION = 8


def detect_spanish(subject, body):
    """Return True if the client's email (subject + body) is confidently
    Spanish. Defaults to False (English) whenever signal is weak or absent
    — precision matters more than recall here.

    Heuristics combined:
      - Spanish marker words/phrases (necesito, por favor, adjunto, seguro,
        certificado, gracias, buenos/buenas, para, dirección, envíame, etc.)
      - Density of Spanish-only characters (ñ, ¿, ¡, accented vowels)
    """
    subject = subject or ""
    body = body or ""
    text = f"{subject}\n{body}".strip()

    if len(text) < _MIN_LEN_FOR_DETECTION:
        return False

    marker_hits = len(_SPANISH_MARKER_RE.findall(text))
    char_hits = len(_SPANISH_CHAR_RE.findall(text))

    # Require multi-signal or strong single-signal confirmation, so a lone
    # incidental match (e.g. "para" inside an English proper noun, unlikely
    # but possible) doesn't flip an English email to Spanish by itself.
    if marker_hits >= 2:
        return True
    if marker_hits >= 1 and char_hits >= 1:
        return True
    # Accented-character density alone: require several distinct hits so a
    # single stray character (e.g. a copy-pasted name like "José") doesn't
    # flip an otherwise-English email.
    if char_hits >= 3:
        return True

    return False
