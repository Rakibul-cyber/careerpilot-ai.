# Deterministic rule-based scorer for resume-to-job matching (M29).
#
# Pure and side-effect free: given a ResumeProfile and a Job it returns a
# ScoreResult. No DB, no AI, no embeddings, no randomness — the same inputs
# always yield the same output (all set-derived lists are sorted). Smarter,
# semantic matching arrives in M31; this is the honest baseline.
#
# Weights (sum to 100):
#   skills            50   coverage of the candidate's skills in the job text
#   title relevance   20   overlap of job-title terms with the candidate corpus
#   experience        15   number of prior roles (capped at 3)
#   location+language 15   location fit (10) + language fit (5)

import re
from dataclasses import dataclass

from app.models.job import Job
from app.models.resume_profile import ResumeProfile

WEIGHT_SKILLS = 50.0
WEIGHT_TITLE = 20.0
WEIGHT_EXPERIENCE = 15.0
WEIGHT_LOCATION = 10.0
WEIGHT_LANGUAGE = 5.0

# Roles at/above this count earn full experience points.
FULL_EXPERIENCE_ROLES = 3

# Tokens too generic to carry title signal.
_STOPWORDS = frozenset(
    {
        "a", "an", "and", "the", "of", "for", "to", "in", "on", "with", "at",
        "by", "or", "as", "is", "be", "we", "you", "our", "your",
        "senior", "junior", "lead", "staff", "principal",
        "m", "f", "d", "mfd", "m_f_d",
    }
)

# Languages we can recognize deterministically, keyed to detection aliases.
_LANGUAGE_ALIASES = {
    "german": ("german", "deutsch"),
    "english": ("english", "englisch"),
    "french": ("french", "franzosisch", "français"),
    "spanish": ("spanish", "spanisch", "español"),
    "italian": ("italian", "italienisch"),
    "dutch": ("dutch", "niederlandisch"),
}

_REMOTE_HINTS = frozenset({"remote", "hybrid"})


@dataclass
class ScoreResult:
    overall_score: float
    skill_score: float
    title_score: float
    location_score: float
    experience_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    match_reasons: list[str]
    risk_flags: list[str]
    raw_match_data: dict


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    return {
        tok
        for tok in re.split(r"[^a-z0-9+#]+", text.lower())
        if len(tok) > 1 and tok not in _STOPWORDS
    }


def _phrase_in_text(phrase: str, text: str) -> bool:
    """True if ``phrase`` occurs in ``text`` (word-boundary aware).

    Falls back to substring for phrases containing non-word characters (e.g.
    ``c++``) where ``\\b`` boundaries don't behave.
    """
    phrase = phrase.strip().lower()
    if not phrase:
        return False
    if re.fullmatch(r"[a-z0-9 ]+", phrase):
        return re.search(rf"\b{re.escape(phrase)}\b", text) is not None
    return phrase in text


def _dedup_preserve(values) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values or []:
        if not isinstance(v, str):
            continue
        key = v.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(v.strip())
    return out


class JobMatchScoringService:
    """Rule-based, deterministic resume-to-job scorer."""

    def score(self, profile: ResumeProfile, job: Job) -> ScoreResult:
        job_text = " ".join(
            filter(
                None,
                [job.title, job.normalized_title, job.description,
                 job.requirements],
            )
        ).lower()

        reasons: list[str] = []
        risks: list[str] = []

        skill_score, matched_skills, missing_skills, skill_ratio = (
            self._score_skills(profile, job_text, reasons, risks)
        )
        title_score, title_ratio, title_hits = self._score_title(
            profile, job, reasons
        )
        experience_score, role_count = self._score_experience(
            profile, reasons, risks
        )
        location_score, loc_detail = self._score_location_language(
            profile, job, job_text, reasons, risks
        )

        overall = round(
            min(
                100.0,
                max(
                    0.0,
                    skill_score + title_score + experience_score
                    + location_score,
                ),
            ),
            2,
        )

        raw = {
            "weights": {
                "skills": WEIGHT_SKILLS,
                "title": WEIGHT_TITLE,
                "experience": WEIGHT_EXPERIENCE,
                "location": WEIGHT_LOCATION,
                "language": WEIGHT_LANGUAGE,
            },
            "skills": {
                "ratio": round(skill_ratio, 4),
                "matched_count": len(matched_skills),
                "missing_count": len(missing_skills),
            },
            "title": {
                "ratio": round(title_ratio, 4),
                "matched_terms": title_hits,
            },
            "experience": {"role_count": role_count},
            "location_language": loc_detail,
        }

        return ScoreResult(
            overall_score=overall,
            skill_score=round(skill_score, 2),
            title_score=round(title_score, 2),
            location_score=round(location_score, 2),
            experience_score=round(experience_score, 2),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            match_reasons=reasons,
            risk_flags=risks,
            raw_match_data=raw,
        )

    # --- component scorers -------------------------------------------------

    def _score_skills(self, profile, job_text, reasons, risks):
        skills = _dedup_preserve(profile.skills)
        if not skills:
            risks.append("no_skills_on_profile")
            reasons.append("Profile lists no skills to match against.")
            return 0.0, [], [], 0.0

        matched = [s for s in skills if _phrase_in_text(s, job_text)]
        missing = [s for s in skills if s not in matched]
        ratio = len(matched) / len(skills)
        score = ratio * WEIGHT_SKILLS
        reasons.append(
            f"Matched {len(matched)}/{len(skills)} of your skills in the job "
            f"posting."
        )
        if not matched:
            risks.append("no_skill_overlap")
        return score, sorted(matched, key=str.lower), \
            sorted(missing, key=str.lower), ratio

    def _score_title(self, profile, job, reasons):
        title_tokens = _tokenize(job.normalized_title or job.title)
        if not title_tokens:
            return 0.0, 0.0, []

        corpus = set()
        for exp in profile.work_experience or []:
            if isinstance(exp, dict):
                corpus |= _tokenize(exp.get("title"))
        for s in profile.skills or []:
            corpus |= _tokenize(s if isinstance(s, str) else None)
        corpus |= _tokenize(profile.summary)

        hits = sorted(title_tokens & corpus)
        ratio = len(hits) / len(title_tokens)
        score = ratio * WEIGHT_TITLE
        if hits:
            reasons.append(
                "Job title overlaps your background on: "
                + ", ".join(hits)
                + "."
            )
        return score, ratio, hits

    def _score_experience(self, profile, reasons, risks):
        roles = [
            e for e in (profile.work_experience or []) if isinstance(e, dict)
        ]
        count = len(roles)
        if count == 0:
            risks.append("no_work_experience")
            reasons.append("Profile lists no work experience.")
            return 0.0, 0
        ratio = min(count / FULL_EXPERIENCE_ROLES, 1.0)
        reasons.append(
            f"{count} prior role(s) on your profile."
        )
        return ratio * WEIGHT_EXPERIENCE, count

    def _score_location_language(self, profile, job, job_text, reasons, risks):
        detail: dict = {}

        # --- location (10) ---
        job_loc = (job.location or "").strip()
        remote = (job.remote_type or "").strip().lower() in _REMOTE_HINTS
        cand_loc = (profile.location or "").strip()
        if not job_loc or remote:
            loc_points = WEIGHT_LOCATION
            detail["location"] = "remote_or_unspecified"
            reasons.append("Location is remote/flexible or unspecified.")
        elif not cand_loc:
            loc_points = WEIGHT_LOCATION / 2
            detail["location"] = "candidate_location_unknown"
            risks.append("candidate_location_unknown")
        elif _tokenize(cand_loc) & _tokenize(job_loc):
            loc_points = WEIGHT_LOCATION
            detail["location"] = "match"
            reasons.append(f"Your location matches the job location "
                           f"({job_loc}).")
        else:
            loc_points = 0.0
            detail["location"] = "mismatch"
            risks.append("location_mismatch")
            reasons.append(
                f"Your location ({cand_loc}) differs from the job location "
                f"({job_loc})."
            )

        # --- language (5) ---
        required = self._detect_languages(job_text)
        candidate = self._candidate_languages(profile.languages)
        detail["required_languages"] = sorted(required)
        detail["candidate_languages"] = sorted(candidate)
        if not required:
            lang_points = WEIGHT_LANGUAGE
            detail["language"] = "no_requirement"
        else:
            have = required & candidate
            ratio = len(have) / len(required)
            lang_points = ratio * WEIGHT_LANGUAGE
            detail["language"] = f"{len(have)}/{len(required)}"
            if ratio < 1.0:
                risks.append("language_requirement_unmet")
                missing_langs = sorted(required - candidate)
                reasons.append(
                    "Job appears to require language(s) you don't list: "
                    + ", ".join(missing_langs)
                    + "."
                )

        detail["location_points"] = round(loc_points, 2)
        detail["language_points"] = round(lang_points, 2)
        return loc_points + lang_points, detail

    @staticmethod
    def _detect_languages(job_text: str) -> set[str]:
        found = set()
        for lang, aliases in _LANGUAGE_ALIASES.items():
            if any(_re_word(a, job_text) for a in aliases):
                found.add(lang)
        return found

    @staticmethod
    def _candidate_languages(languages) -> set[str]:
        found = set()
        for entry in languages or []:
            if not isinstance(entry, str):
                continue
            low = entry.lower()
            for lang, aliases in _LANGUAGE_ALIASES.items():
                if any(a in low for a in aliases):
                    found.add(lang)
        return found


def _re_word(word: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None
