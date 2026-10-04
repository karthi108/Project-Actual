"""Leakage detection for public split-plan metadata; never reads frozen test data."""

import hashlib
import re
from dataclasses import fields

from .codec import record_data
from .contracts import ScenarioInput, SplitMembership
from .validation import Violation


def source_fingerprints(value: ScenarioInput) -> set[str]:
    hashes: set[str] = set()
    for job in value.jobs:
        text = f"{job.title} {job.text}".casefold()
        for name in [c.name for c in value.companies] + [value.candidate.name]:
            text = text.replace(name.casefold(), " entity ")
        text = re.sub(r"https?://\S+", " url ", text)
        text = re.sub(r"\b[abc][12]\b", " cefr ", text)
        text = re.sub(r"\d+", " number ", text)
        text = " ".join(re.findall(r"\w+", text))
        hashes.add(hashlib.sha256(text.encode("utf-8")).hexdigest())
    return hashes


def content_fingerprint(value: ScenarioInput) -> str:
    return hashlib.sha256("\n".join(sorted(source_fingerprints(value))).encode()).hexdigest()


def validate_split_isolation(
    memberships: tuple[SplitMembership, ...], inputs: tuple[ScenarioInput, ...]
) -> tuple[Violation, ...]:
    errors: list[Violation] = []
    scenarios = {item.id: item for item in inputs}
    mapping = {item.scenario_id: item for item in memberships}
    if (
        len(mapping) != len(memberships)
        or len(scenarios) != len(inputs)
        or set(mapping) != set(scenarios)
    ):
        return (
            Violation(
                "split_membership", "split_plan", "Exactly one membership per input required"
            ),
        )
    parent = {item.scenario_id: item.scenario_id for item in memberships}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    seen: dict[tuple[str, str], str] = {}
    sources: dict[str, str] = {}
    for member in memberships:
        record_data(member)
        if member.normalized_content_hash != content_fingerprint(scenarios[member.scenario_id]):
            errors.append(
                Violation("fingerprint_mismatch", member.scenario_id, "Computed hash differs")
            )
        for field in fields(member):
            if not field.name.endswith("_lineages"):
                continue
            keys: tuple[str, ...] = getattr(member, field.name)
            if not keys or len(set(keys)) != len(keys) or any(not key.strip() for key in keys):
                errors.append(
                    Violation("split_membership", member.scenario_id, "Empty/duplicate lineage")
                )
            for key in keys:
                namespaced = (field.name, key)
                if namespaced in seen:
                    other = seen[namespaced]
                    parent[find(member.scenario_id)] = find(other)
                seen[namespaced] = member.scenario_id
        for fingerprint in source_fingerprints(scenarios[member.scenario_id]):
            if fingerprint in sources and mapping[sources[fingerprint]].split != member.split:
                errors.append(
                    Violation(
                        "duplicate_source", member.scenario_id, "Normalized source crosses split"
                    )
                )
            sources[fingerprint] = member.scenario_id
    components: dict[str, set[str]] = {}
    for member in memberships:
        components.setdefault(find(member.scenario_id), set()).add(member.split)
    for component, split_names in components.items():
        if len(split_names) > 1:
            errors.append(
                Violation("shared_lineage", component, "Connected lineage crosses splits")
            )
    return tuple(errors)
