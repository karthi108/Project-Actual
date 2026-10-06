"""Observable segmentation and a small precision-first explicit grammar."""

import re
from dataclasses import dataclass, field, replace

from actual.career.jobs import Job

from .errors import IntelligenceFailure

EXTRACTION_VERSION = "source-extraction-v2"
_SUBJECT = (
    r"(?:local[- ]model integration|local LLM integration|LLM integration|"
    r"Microsoft Azure|Python development|Fast API|FastAPI|Python|Azure|French|"
    r"backend experience|work experience|experience)"
)
_IMPORTANCE = r"(?:essential|required|mandatory|preferred|optional)"
_COUNT = r"(?:[0-9]+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
_EXPLICIT = re.compile(
    rf"(?:{_SUBJECT} at (?:introductory|working|strong) level (?:is|are) {_IMPORTANCE}"
    rf"|(?:introductory|working|strong) {_SUBJECT} (?:is|are) {_IMPORTANCE}"
    rf"|French [ABC][12] (?:is|are) {_IMPORTANCE}"
    rf"|{_COUNT}\+? (?:years?|months?) of (?:backend )?experience (?:is|are) {_IMPORTANCE}"
    rf"|[A-Za-z][A-Za-z0-9_.-]*(?: certification)? (?:is )?{_IMPORTANCE})[.!?;]?",
    re.IGNORECASE,
)
_CONCEPT = re.compile(rf"\b{_SUBJECT}\b", re.IGNORECASE)
_DIRECTIVE = re.compile(
    r"\[/?(?:system|developer)\]|</?(?:system|developer)>|"
    r"\b(?:system|developer)\s*(?::|command|authority|prompt)|"
    r"\b(?:ignore|omit|hide|fabricate|invent|reveal|disclose|print|execute)\b|"
    r"\bperfect\s+(?:fit|match)\b",
    re.IGNORECASE,
)
_BOUNDARIES = re.compile(
    r"</?(?:system|developer)>|\[/?(?:system|developer)\]|[.!?](?=\s|$)|;|\n",
    re.IGNORECASE,
)
_ROLE_MARKERS = re.compile(
    r"<(?P<xml_close>/)?(?P<xml_role>system|developer)>|"
    r"\[(?P<bracket_close>/)?(?P<bracket_role>system|developer)\]",
    re.IGNORECASE,
)
_DEPENDENT_PREFIX = re.compile(
    r"\s*(?:whether|but|however|although|unless|except|not|or|and|"
    r"for|with|in|at|it|this|that)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DocumentSegment:
    id: int
    start: int
    end: int
    text: str = field(repr=False)
    role_context: bool = False


@dataclass(frozen=True)
class ExtractedAtom:
    source_id: int
    quote: str = field(repr=False)
    term: str = field(repr=False)
    source_start: int
    source_end: int
    term_start: int
    term_end: int
    method: str


def segment_document(job: Job) -> tuple[DocumentSegment, ...]:
    if len(job.text.encode("utf-8")) > 1024:
        raise IntelligenceFailure("input_rejected")
    values: list[DocumentSegment] = []
    start = 0
    for boundary in _BOUNDARIES.finditer(job.text):
        if boundary.group().startswith(("<", "[")) and job.text[start : boundary.start()].strip():
            left = (
                start
                + len(job.text[start : boundary.start()])
                - len(job.text[start : boundary.start()].lstrip())
            )
            right = len(job.text[: boundary.start()].rstrip())
            values.append(DocumentSegment(len(values), left, right, job.text[left:right]))
            start = boundary.start()
        stop = boundary.end()
        left = start
        while left < stop and job.text[left].isspace():
            left += 1
        right = stop
        while right > left and job.text[right - 1].isspace():
            right -= 1
        if right > left:
            values.append(DocumentSegment(len(values), left, right, job.text[left:right]))
        start = stop
    if job.text[start:].strip():
        left = start + len(job.text[start:]) - len(job.text[start:].lstrip())
        right = len(job.text.rstrip())
        values.append(DocumentSegment(len(values), left, right, job.text[left:right]))
    if not values or len(values) > 32:
        raise IntelligenceFailure("input_rejected")
    # Segmenting role markers must not turn their enclosed source into ordinary
    # employer text. Unclosed/mismatched role wrappers conservatively taint the
    # remainder; correctly closed wrappers do not taint independent later clauses.
    stack: list[tuple[str, str, int]] = []
    tainted: list[tuple[int, int]] = []
    for marker in _ROLE_MARKERS.finditer(job.text):
        style = "xml" if marker.group("xml_role") is not None else "bracket"
        role = (marker.group("xml_role") or marker.group("bracket_role")).casefold()
        closing = marker.group("xml_close") or marker.group("bracket_close")
        tainted.append((marker.start(), marker.end()))
        if not closing:
            stack.append((style, role, marker.start()))
        elif stack and stack[-1][:2] == (style, role):
            _, _, opened = stack.pop()
            tainted.append((opened, marker.end()))
    tainted.extend((opened, len(job.text)) for _, _, opened in stack)
    scoped = tuple(
        replace(
            segment,
            role_context=any(segment.start < end and start < segment.end for start, end in tainted),
        )
        for segment in values
    )
    contextual: list[DocumentSegment] = []
    for segment in scoped:
        previous = contextual[-1] if contextual else None
        if (
            previous is not None
            and previous.text.endswith(";")
            and not previous.role_context
            and not segment.role_context
            and not _independent_clause(segment.text)
        ):
            contextual[-1] = DocumentSegment(
                previous.id, previous.start, segment.end, job.text[previous.start : segment.end]
            )
        else:
            contextual.append(segment)
    return tuple(replace(segment, id=index) for index, segment in enumerate(contextual))


def instruction_like(text: str) -> bool:
    return _DIRECTIVE.search(text) is not None


def _independent_clause(text: str) -> bool:
    """Semicolon qualifiers remain attached; independent commands stay separate."""
    if instruction_like(text):
        return True
    if _DEPENDENT_PREFIX.match(text):
        return False
    if _EXPLICIT.fullmatch(text):
        return True
    return (
        re.search(
            r"\b(?:essential|required|mandatory|preferred|optional|helpful|plus)\b",
            text,
            re.IGNORECASE,
        )
        is not None
        and _CONCEPT.search(text) is not None
    )


def explicit_sources(segments: tuple[DocumentSegment, ...]) -> tuple[int, ...]:
    return tuple(
        source.id
        for source in segments
        if not source.role_context
        and not instruction_like(source.text)
        and _EXPLICIT.fullmatch(source.text) is not None
    )


def source_atoms(source: DocumentSegment, *, method: str) -> tuple[ExtractedAtom, ...]:
    if method not in ("qwen", "deterministic"):
        raise ValueError("Known extraction origin is required")
    if source.role_context or instruction_like(source.text):
        return ()
    mentions = list(_CONCEPT.finditer(source.text))
    if not mentions:
        term = source.text[:64].rstrip()
        return (
            ExtractedAtom(
                source.id,
                source.text,
                term,
                source.start,
                source.end,
                source.start,
                source.start + len(term),
                method,
            ),
        )
    return tuple(
        ExtractedAtom(
            source.id,
            source.text,
            item.group(),
            source.start,
            source.end,
            source.start + item.start(),
            source.start + item.end(),
            method,
        )
        for item in mentions
    )
