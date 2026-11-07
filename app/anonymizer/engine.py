
from app.anonymizer.rules import DEFAULT_RULES, Rule


class AnonymizationEngine:
    """Finds rule matches, resolves overlaps by priority, then masks right-to-left."""

    def __init__(self, rules: list[Rule] | None = None):
        self.rules = rules if rules is not None else DEFAULT_RULES

    def anonymize(self, text: str) -> tuple[str, dict[str, int]]:
        candidates = []

        # Find all matches from all rules.
        for rule in self.rules:
            for match in rule.pattern.finditer(text):
                value = match.group(0)

                # Skip matches that the masker does not change.
                if rule.masker(value) == value:
                    continue

                candidates.append({
                    "start": match.start(),
                    "end": match.end(),
                    "value": value,
                    "rule": rule,
                })

        # Higher-priority matches win.
        # If priorities are equal, the longer match wins.
        candidates.sort(
            key=lambda item: (
                item["rule"].priority,
                item["end"] - item["start"],
            ),
            reverse=True,
        )

        # Resolve overlapping matches.
        selected = []

        for candidate in candidates:
            overlaps = any(
                candidate["start"] < item["end"]
                and item["start"] < candidate["end"]
                for item in selected
            )

            if not overlaps:
                selected.append(candidate)

        # Count only matches that will actually be masked.
        counts: dict[str, int] = {}

        for item in selected:
            name = item["rule"].name
            counts[name] = counts.get(name, 0) + 1

        # Apply masks from right to left to preserve positions.
        result = text

        for item in sorted(
            selected,
            key=lambda x: x["start"],
            reverse=True,
        ):
            replacement = item["rule"].masker(item["value"])

            result = (
                result[:item["start"]]
                + replacement
                + result[item["end"]:]
            )

        return result, counts

