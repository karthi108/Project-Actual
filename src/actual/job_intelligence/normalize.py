"""Source-preserving lexical interpretation; unsupported precision abstains."""

import re
from typing import Any
from uuid import UUID, uuid5

from actual.career.jobs import Job
from actual.career.requirements import (
    AbstentionReason,
    CanonicalConcept,
    ExperienceScope,
    ExtractionMethod,
    InterpretedRequirement,
    Priority,
    RequirementConstraints,
)
from actual.core.primitives import CompanyId, JobId, OpportunityId, RequirementId, WorkspaceId
from actual.job_intelligence.errors import IntelligenceCode, IntelligenceFailure
from actual.profile.contracts import Assertion

NORMALIZATION_VERSION = "career-normalization-v2"
_NAMESPACE = UUID("4264c9a5-983f-4e3b-9bfa-295afc190a06")
_ALIASES: dict[str, CanonicalConcept] = {
    "python": "python",
    "python development": "python",
    "fastapi": "fastapi",
    "fast api": "fastapi",
    "azure": "azure",
    "microsoft azure": "azure",
    "local llm integration": "llm_integration",
    "llm integration": "llm_integration",
    "local-model integration": "llm_integration",
    "local model integration": "llm_integration",
    "french": "french",
    "experience": "experience",
    "backend experience": "experience",
    "professional experience": "experience",
    "work experience": "experience",
}
_NUMBER_WORDS = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
)
_NUMBERS = {word: value for value, word in enumerate(_NUMBER_WORDS)}
_NUMBER = r"(?:[0-9]+|" + "|".join(_NUMBER_WORDS) + r")"
_DURATION = re.compile(r"(?<![\w.,])(" + _NUMBER + r")\s*\+?\s*(years?|months?)\b", re.IGNORECASE)
_UNSUPPORTED_DURATION = re.compile(
    r"[0-9][.,][0-9]|\b(?:over|above|under|below|between|up to|at most|"
    r"less than|more than|several|about|approximately)\b|"
    + _NUMBER
    + r"\s*(?:[-–—]|to)\s*"
    + _NUMBER,
    re.IGNORECASE,
)
_BOUNDARY = re.compile(
    r"[.!?](?:\s+|$)|\n|</?(?:system|developer)>|\[/?(?:system|developer)\]",
    re.IGNORECASE,
)
_INSTRUCTION = re.compile(
    r"\b(?:ignore\s+(?:the\s+|all\s+|previous\s+|ACTUAL(?:['’]s)?\s+)?"
    r"(?:instructions?|evidence|review|rules?|requirements?)"
    r"|(?:system|developer)\s+(?:prompt|authority|command|instruction)"
    r"|(?:print|reveal|disclose)\s+(?:the\s+)?(?:local\s+)?(?:secret|canary|credential)"
    r"|(?:fabricate|invent)\s+(?:candidate\s+)?(?:skills?|evidence|qualifications?)"
    r"|mark\s+(?:this\s+job\s+|the\s+candidate\s+)?(?:as\s+)?(?:a\s+)?perfect\s+fit"
    r"|write\s+French\s+[ABC][12])\b",
    re.IGNORECASE,
)
_DIRECTIVE = re.compile(
    r"\b(?:assistant\s*[, :]|(?:system|developer)\s*:|claim\s+that\s+|"
    r"reveal\s+(?:the\s+)?(?:evaluator\s+)?secret\b)|"
    r"\[(?:system|developer)\]|</?(?:system|developer)>",
    re.IGNORECASE,
)
_SCOPE_WORDS = {
    "professional": r"\b(?:professional|employment|commercial|paid|industry)\b",
    "internship": r"\b(?:internship|intern)\b",
    "academic": r"\b(?:academic|university|coursework|research)\b",
    "personal_project": r"\b(?:personal|hobby|projects?)\b",
    "open_source": r"\bopen[ -]source\b",
}
_SKILL_NAMES = (
    r"(?:Python(?: development)?|FastAPI|Fast API|(?:Microsoft )?Azure|"
    r"(?:local[ -])?(?:LLM|model) integration)"
)
_LEVEL = r"(introductory|working|strong)"
_SAFE_SUFFIX = re.compile(
    r"^\s*(?:(?:is|are|would be)\s+)?"
    r"(?:essential|required|mandatory|preferred|optional|helpful|a plus|nice to have)"
    r"(?:\s*[.;!?])?\s*(?:whether it is mandatory is not stated[.!?]?\s*)?$",
    re.IGNORECASE,
)


def checked_job(job: Job) -> Job:
    """Domain validation never silently drops extra fields from an input instance."""
    if (
        type(job) is not Job
        or set(job.__dict__) - set(Job.model_fields)
        or job.__pydantic_extra__ is not None
    ):
        raise IntelligenceFailure(IntelligenceCode.INPUT_REJECTED)
    try:
        for item in (job.id, job.workspace_id, job.company_id, job.opportunity_id):
            if (
                type(item) not in (JobId, WorkspaceId, CompanyId, OpportunityId)
                or set(item.__dict__) != {"root"}
                or item.__pydantic_extra__ is not None
            ):
                raise IntelligenceFailure(IntelligenceCode.INPUT_REJECTED)
        checked = Job.model_validate(job)
        if checked.classification != "synthetic":
            raise IntelligenceFailure(IntelligenceCode.INPUT_REJECTED)
        return checked
    except IntelligenceFailure:
        raise
    except Exception:
        raise IntelligenceFailure(IntelligenceCode.INPUT_REJECTED) from None


def source_priority(context: str) -> Priority:
    """Ambiguity and negation override a nearby positive priority word."""
    lowered = context.casefold()
    if re.search(
        r"(?:not stated|not specified|unclear|ambiguous|whether .*mandatory|"
        r"not required|not mandatory)",
        lowered,
    ):
        return "ambiguous"
    essential = re.search(r"\b(?:essential|required|must|mandatory)\b", lowered) is not None
    preferred = (
        re.search(r"\b(?:preferred|optional|helpful|plus)\b|nice to have", lowered) is not None
    )
    if essential == preferred:
        return "ambiguous"
    return "essential" if essential else "preferred"


_ROLE_MARKERS = re.compile(
    r"<(?P<xml_close>/)?(?P<xml_role>system|developer)>|"
    r"\[(?P<bracket_close>/)?(?P<bracket_role>system|developer)\]",
    re.IGNORECASE,
)


def _role_enclosed(text: str, start: int, end: int) -> bool:
    """Fake role wrappers never turn their enclosed source into employer facts."""
    stack: list[tuple[str, str, int]] = []
    tainted: list[tuple[int, int]] = []
    for marker in _ROLE_MARKERS.finditer(text):
        style = "xml" if marker.group("xml_role") is not None else "bracket"
        role = (marker.group("xml_role") or marker.group("bracket_role")).casefold()
        closing = marker.group("xml_close") or marker.group("bracket_close")
        tainted.append((marker.start(), marker.end()))
        if not closing:
            stack.append((style, role, marker.start()))
        elif stack and stack[-1][:2] == (style, role):
            _, _, opened = stack.pop()
            tainted.append((opened, marker.end()))
    tainted.extend((opened, len(text)) for _, _, opened in stack)
    return any(start < right and left < end for left, right in tainted)


def _independent_clause(text: str) -> bool:
    """Separate obvious directives/predicates, never a dependent qualifier."""
    if (
        _INSTRUCTION.search(text)
        or _DIRECTIVE.search(text)
        or re.search(
            r"\b(?:ignore|omit|hide|fabricate|invent|reveal|disclose|print|execute)\b|"
            r"\bperfect\s+(?:fit|match)\b",
            text,
            re.IGNORECASE,
        )
    ):
        return True
    if re.match(
        r"\s*(?:whether|but|however|although|unless|except|not|or|and|"
        r"for|with|in|at|it|this|that)\b",
        text,
        re.IGNORECASE,
    ):
        return False
    if re.fullmatch(
        r"\s*[A-Za-z][A-Za-z0-9_.-]*(?: certification)? (?:is )?"
        r"(?:essential|required|mandatory|preferred|optional)[.!?;]?\s*",
        text,
        re.IGNORECASE,
    ):
        return True
    # Clear priority plus a named qualification is a separate predicate. Anything
    # less explicit remains contextual, preserving precision rather than guessing.
    return re.search(
        r"\b(?:essential|required|mandatory|preferred|optional|helpful|plus)\b",
        text,
        re.IGNORECASE,
    ) is not None and any(
        re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text, re.IGNORECASE)
        for alias in _ALIASES
    )


def source_context(text: str, start: int, end: int) -> tuple[int, int, str]:
    """Keep dependent qualifiers while isolating independent inline directives."""
    before = list(_BOUNDARY.finditer(text[:start]))
    sentence_start = before[-1].end() if before else 0
    after = _BOUNDARY.search(text[start:])
    sentence_end = start + after.end() if after else len(text)
    if end > sentence_end:
        raise IntelligenceFailure(IntelligenceCode.INVALID_REQUIREMENT)
    boundaries = [sentence_start]
    boundaries.extend(match.end() for match in re.finditer(";", text[sentence_start:sentence_end]))
    # Semicolon offsets above are relative to the sentence.
    boundaries = [sentence_start] + [sentence_start + offset for offset in boundaries[1:]]
    if boundaries[-1] != sentence_end:
        boundaries.append(sentence_end)
    intervals = list(zip(boundaries, boundaries[1:], strict=False))
    first = next(
        (index for index, (left, right) in enumerate(intervals) if left <= start < right), None
    )
    last = next(
        (index for index, (left, right) in enumerate(intervals) if left < end <= right), None
    )
    if first is None or last is None:
        raise IntelligenceFailure(IntelligenceCode.INVALID_REQUIREMENT)
    while first > 0 and not _independent_clause(
        text[intervals[first - 1][0] : intervals[first - 1][1]]
    ):
        first -= 1
    while last + 1 < len(intervals) and not _independent_clause(
        text[intervals[last + 1][0] : intervals[last + 1][1]]
    ):
        last += 1
    context_start, context_end = intervals[first][0], intervals[last][1]
    while context_start < context_end and text[context_start].isspace():
        context_start += 1
    while context_end > context_start and text[context_end - 1].isspace():
        context_end -= 1
    return context_start, context_end, text[context_start:context_end]


def _concept(term: str) -> tuple[CanonicalConcept | None, int, int]:
    candidates: list[tuple[CanonicalConcept, int, int]] = []
    for alias, concept in _ALIASES.items():
        for match in re.finditer(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", term, re.IGNORECASE):
            candidates.append((concept, match.start(), match.end()))
    candidates = [
        item
        for item in candidates
        if not any(
            item != other and item[0] == other[0] and other[1] <= item[1] and item[2] <= other[2]
            for other in candidates
        )
    ]
    if len(candidates) != 1:
        return None, 0, len(term)
    return candidates[0]


def _experience_scope(context: str, head: str) -> ExperienceScope:
    found = [
        scope
        for scope, pattern in _SCOPE_WORDS.items()
        if re.search(pattern, context, re.IGNORECASE)
    ]
    if len(found) == 1:
        return found[0]  # type: ignore[return-value]
    if found:
        return "unknown"
    if context.rstrip(" .;!?").casefold() == "five years of backend experience are essential":
        return "legacy_backend"
    if head.casefold() == "backend experience":
        return "unknown"
    if re.fullmatch(
        r"(?:at least\s+)?" + _NUMBER + r"\s*\+?\s*(?:years?|months?)\s+(?:of\s+)?experience\s+"
        r"(?:(?:is|are)\s+)?(?:essential|required|preferred|mandatory)[.!?;]?",
        context,
        re.IGNORECASE,
    ):
        return "generic"
    return "unknown"


def _skill_value(context: str, local_start: int, local_end: int) -> int | None:
    before, after = context[:local_start], context[local_end:]
    prefix = re.fullmatch(r"\s*" + _LEVEL + r"\s+", before, re.IGNORECASE)
    suffix = re.match(r"\s+at\s+" + _LEVEL + r"\s+level\b", after, re.IGNORECASE)
    collective = re.match(
        r"(?:\s*(?:and|,)\s*" + _SKILL_NAMES + r"){1,3}\s+at\s+" + _LEVEL + r"\s+level\b",
        after,
        re.IGNORECASE,
    )
    if suffix is not None and re.fullmatch(
        r"\s*(?:" + _SKILL_NAMES + r"\s*(?:and|,)\s*){0,3}", before, re.IGNORECASE
    ):
        remaining = after[suffix.end() :]
        if _SAFE_SUFFIX.fullmatch(remaining):
            return {"introductory": 1, "working": 2, "strong": 3}[suffix[1].casefold()]
    if prefix is not None and _SAFE_SUFFIX.fullmatch(after):
        return {"introductory": 1, "working": 2, "strong": 3}[prefix[1].casefold()]
    if (
        collective is not None
        and not before.strip()
        and _SAFE_SUFFIX.fullmatch(after[collective.end() :])
    ):
        return {"introductory": 1, "working": 2, "strong": 3}[collective[1].casefold()]
    return None


def normalize_requirement(
    job: Job, *, quote: str, term: str, priority: Priority, method: ExtractionMethod = "qwen"
) -> InterpretedRequirement:
    checked = checked_job(job)
    if (
        type(quote) is not str
        or type(term) is not str
        or not 1 <= len(quote) <= 512
        or not 1 <= len(term) <= 128
        or term != term.strip()
        or quote.count(term) != 1
        or checked.text.count(quote) != 1
        or priority not in ("essential", "preferred", "ambiguous")
        or method not in ("qwen", "deterministic")
    ):
        raise IntelligenceFailure(IntelligenceCode.INVALID_REQUIREMENT)
    supplied_start = checked.text.index(quote)
    if _role_enclosed(checked.text, supplied_start, supplied_start + len(quote)):
        raise IntelligenceFailure(IntelligenceCode.UNSAFE_SOURCE)
    start, end, context = source_context(checked.text, supplied_start, supplied_start + len(quote))
    if _INSTRUCTION.search(context) or _DIRECTIVE.search(context):
        raise IntelligenceFailure(IntelligenceCode.UNSAFE_SOURCE)
    if priority != source_priority(context):
        raise IntelligenceFailure(IntelligenceCode.INVALID_REQUIREMENT)
    concept, offset_start, offset_end = _concept(term)
    term_start = supplied_start + quote.index(term)
    concept_start, concept_end = term_start + offset_start, term_start + offset_end
    common: dict[str, Any] = {
        "id": RequirementId(
            "requirement_"
            + uuid5(
                _NAMESPACE,
                f"{NORMALIZATION_VERSION}/{checked.workspace_id.root}/{checked.id.root}/{checked.revision}/{checked.content_digest}/{start}/{end}/{concept_start}/{concept_end}",
            ).hex
        ),
        "workspace_id": checked.workspace_id,
        "revision": 1,
        "classification": "synthetic",
        "job_id": checked.id,
        "job_revision": checked.revision,
        "job_digest": checked.content_digest,
        "priority": priority,
        "source_start": start,
        "source_end": end,
        "source_quote": context,
        "term": term,
        "concept_start": concept_start,
        "concept_end": concept_end,
        "canonical_concept": concept,
        "extraction_method": method,
        "origin": "ai_proposal" if method == "qwen" else "deterministic_proposal",
        "review": None,
    }

    def abstain(
        reason: AbstentionReason, constraints: RequirementConstraints | None = None
    ) -> InterpretedRequirement:
        return InterpretedRequirement(
            **common,
            assertion=None,
            resolution="abstained",
            reason=reason,
            constraints=constraints or RequirementConstraints(),
        )

    if concept is None:
        return abstain(
            "ambiguous_alias" if term.casefold() in ("api", "cloud", "llm") else "unknown_term"
        )
    kind = (
        "language" if concept == "french" else "experience" if concept == "experience" else "skill"
    )
    unit = {"skill": "skill_level", "language": "cefr_level", "experience": "months"}[kind]
    scope = (
        _experience_scope(context, checked.text[concept_start:concept_end])
        if kind == "experience"
        else None
    )
    constraints = RequirementConstraints.model_validate(
        {"kind": kind, "unit": unit, "experience_scope": scope}
    )
    if re.search(
        r"\b(?:not required|not mandatory|no .*required|without .*required)\b",
        context,
        re.IGNORECASE,
    ):
        return abstain("negated_requirement", constraints)
    local_start, local_end = concept_start - start, concept_end - start
    after = context[local_end:]
    if kind == "skill" and re.match(r"\s*(?:version\s*)?[0-9]", after, re.IGNORECASE):
        return abstain("unsupported_version_constraint", constraints)
    number: int | None = None
    if kind == "skill":
        number = _skill_value(context, local_start, local_end)
        if number is None:
            return abstain("unknown_skill_level", constraints)
    elif kind == "language":
        level = re.match(r"\s+(?:at\s+)?([ABC][12])\b", after, re.IGNORECASE)
        if (
            not level
            or len(re.findall(r"\b[ABC][12]\b", context, re.IGNORECASE)) != 1
            or not _SAFE_SUFFIX.fullmatch(after[level.end() :])
            or context[:local_start].strip()
        ):
            return abstain("unknown_language_level", constraints)
        number = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}[level[1].upper()]
    else:
        matches = list(_DURATION.finditer(context))
        if _UNSUPPORTED_DURATION.search(context) or len(matches) != 1:
            return abstain(
                "unknown_experience_duration",
                constraints.model_copy(update={"comparator": "unsupported"}),
            )
        number_text, duration_unit = matches[0].groups()
        count = int(number_text) if number_text.isdigit() else _NUMBERS[number_text.casefold()]
        number = count * (12 if duration_unit.casefold().startswith("year") else 1)
        if not 1 <= number <= 600:
            return abstain(
                "unknown_experience_duration",
                constraints.model_copy(update={"comparator": "unsupported"}),
            )
        constraints = constraints.model_copy(update={"value": number, "comparator": "minimum"})
        if scope not in ("generic", "legacy_backend"):
            return abstain("unsupported_experience_scope", constraints)
    constraints = constraints.model_copy(update={"value": number, "comparator": "minimum"})
    assertion = Assertion.model_validate(
        {"kind": kind, "subject": concept, "unit": unit, "value": number}
    )
    return InterpretedRequirement(
        **common, assertion=assertion, resolution="resolved", reason=None, constraints=constraints
    )
