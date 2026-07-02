# Text-normalization helpers used to build dedup keys for companies and jobs.
#
# Stateless and business-logic-free: services call these to compute
# normalized_name / normalized_title. Kept out of repositories on purpose.

import re

# Punctuation noise to strip (each replaced with a space so words stay separated).
_PUNCTUATION_PATTERN = re.compile(r"[.,;:()\[\]{}]")
_WHITESPACE_PATTERN = re.compile(r"\s+")

# Legal-form suffixes removed from company names when they appear as a token.
_COMPANY_SUFFIXES = {"gmbh", "llc", "ltd", "inc", "ag", "se", "ug"}

# Hiring tags removed from job titles (matched as whole space-delimited phrases).
_JOB_TITLE_TAGS = ["m/f/d", "f/m/d", "all genders", "remote", "hybrid"]


def normalize_text(value: str) -> str:
    """Lowercase, strip punctuation noise, and collapse whitespace."""
    text = value.strip().lower()
    text = _PUNCTUATION_PATTERN.sub(" ", text)
    text = _WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


def _remove_phrases(text: str, phrases: list[str]) -> str:
    """Remove each phrase when it stands alone (bounded by whitespace/edges)."""
    for phrase in phrases:
        pattern = re.compile(r"(?<!\S)" + re.escape(phrase) + r"(?!\S)")
        text = pattern.sub(" ", text)
    return text


def normalize_company_name(name: str) -> str:
    """Normalize a company name and drop legal-form suffixes (gmbh, llc, ...)."""
    text = normalize_text(name)
    tokens = [
        token
        for token in text.split(" ")
        if token and token not in _COMPANY_SUFFIXES
    ]
    return " ".join(tokens)


def normalize_job_title(title: str) -> str:
    """Normalize a job title and drop common hiring tags (m/f/d, remote, ...)."""
    text = normalize_text(title)
    text = _remove_phrases(text, _JOB_TITLE_TAGS)
    return _WHITESPACE_PATTERN.sub(" ", text).strip()
