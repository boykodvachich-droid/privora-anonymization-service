from app.anonymizer.rules import DEFAULT_RULES, Rule


class AnonymizationEngine:
    """Finds rule matches, resolves overlaps by priority, then masks right-to-left."""

    def __init__(self, rules: list[Rule] | None = None):
        self.rules = rules if rules is not None else DEFAULT_RULES

    def anonymize(
        self,
        text: str,
        categories: list[str] | None = None,
    ) -> tuple[str, dict[str, int]]:
        active_rules = self.rules

        if categories is not None:
            selected_categories = set(categories)
            active_rules = [
                rule for rule in self.rules
                if rule.name in selected_categories
            ]

        candidates = []

        for rule in active_rules:
            for match in rule.pattern.finditer(text):
                value = match.group(0)

                if rule.masker(value) == value:
                    continue

                candidates.append({
                    "start": match.start(),
                    "end": match.end(),
                    "value": value,
                    "rule": rule,
                })

        candidates.sort(
            key=lambda item: (
                item["rule"].priority,
                item["end"] - item["start"],
            ),
            reverse=True,
        )

        selected = []

        for candidate in candidates:
            overlaps = any(
                candidate["start"] < item["end"]
                and item["start"] < candidate["end"]
                for item in selected
            )

            if not overlaps:
                selected.append(candidate)

        counts: dict[str, int] = {}

        for item in selected:
            name = item["rule"].name
            counts[name] = counts.get(name, 0) + 1

        result = text

        for item in sorted(selected, key=lambda x: x["start"], reverse=True):
            replacement = item["rule"].masker(item["value"])
            result = (
                result[:item["start"]]
                + replacement
                + result[item["end"]:]
            )

        return result, counts