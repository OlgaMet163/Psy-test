from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional


class HoganAtlasInsights:
    """Loads combo-specific domain insights from Derailer Atlas docs."""

    FILE_PATTERNS = {
        "single": "Derailer_Single_Traits_Atlas",
        "pair": "Derailer_Pairs_Atlas",
        "triple": "Derailer_Triples_Atlas",
        "quadruple": "Derailer_Quadruples_Atlas",
    }

    DOMAIN_ALIASES = {
        "career": "career",
        "business": "business",
        "friendships": "friendships",
        "hobbies": "hobbies",
        "romantic": "romantic",
        "overall lifestyle": "lifestyle",
        "lifestyle": "lifestyle",
        "health": "health",
        "sports": "sports",
    }

    def __init__(self, docs_dir: Path | None = None) -> None:
        base_dir = docs_dir or Path(__file__).resolve().parents[2] / "docs"
        self.base_dir = Path(base_dir)
        self._cache: Dict[str, Dict[str, Dict[str, str]]] = {}

    def has_combo(self, combo_type: str, combo_key: str) -> bool:
        combos = self._load_combos(combo_type)
        return combo_key in combos

    def get_domain_text(
        self, combo_type: str, combo_key: str, domain: str
    ) -> Optional[str]:
        combos = self._load_combos(combo_type)
        combo_data = combos.get(combo_key)
        if not combo_data:
            return None
        return combo_data.get(domain.lower())

    def _load_combos(self, combo_type: str) -> Dict[str, Dict[str, str]]:
        if combo_type not in self._cache:
            path = self._locate_file(combo_type)
            self._cache[combo_type] = self._parse_file(path, combo_type)
        return self._cache[combo_type]

    def _locate_file(self, combo_type: str) -> Path:
        pattern = self.FILE_PATTERNS.get(combo_type)
        if not pattern:
            raise ValueError(f"Unknown combo type: {combo_type}")
        matches = sorted(self.base_dir.glob(f"{pattern}*.md"))
        if not matches:
            raise FileNotFoundError(f"Atlas file for {combo_type} not found.")
        return matches[-1]

    def _parse_file(self, path: Path, combo_type: str) -> Dict[str, Dict[str, str]]:
        text = path.read_text(encoding="utf-8")
        sections = {}
        heading_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
        matches = list(heading_pattern.finditer(text))
        for idx, match in enumerate(matches):
            heading = match.group(1)
            key = self._extract_key(heading)
            if not key:
                continue
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            section_text = text[start:end]
            if combo_type == "single":
                domains = self._extract_single_domains(section_text)
            else:
                domains = self._extract_domains(section_text)
            if domains:
                sections[key] = domains
        return sections

    def _extract_key(self, heading: str) -> Optional[str]:
        key_match = re.search(r"\*\*([A-Z0-9+]+)", heading)
        if not key_match:
            return None
        raw_key = key_match.group(1)
        parts = raw_key.split("+")
        parts = sorted(part.strip().upper() for part in parts if part.strip())
        if not parts:
            return None
        if len(parts) == 1:
            return parts[0]
        return "+".join(parts)

    def _extract_domains(self, section_text: str) -> Dict[str, str]:
        domain_pattern = re.compile(r"- \*\*([^*]+)\*\*\s*(.+)")
        domains: Dict[str, str] = {}
        for match in domain_pattern.finditer(section_text):
            name = match.group(1).strip().rstrip(":").lower()
            value = match.group(2).strip()
            slug = self.DOMAIN_ALIASES.get(name)
            if slug and value:
                domains[slug] = value
        return domains

    def _extract_single_domains(self, section_text: str) -> Dict[str, str]:
        block_pattern = re.compile(
            r"^###\s+(Low|Typical|Elevated|High)\s*$", re.MULTILINE
        )
        matches = list(block_pattern.finditer(section_text))
        desired_levels = {"elevated", "high"}
        collected: Dict[str, str] = {}
        for idx, match in enumerate(matches):
            level = match.group(1).lower()
            start = match.end()
            end = (
                matches[idx + 1].start()
                if idx + 1 < len(matches)
                else len(section_text)
            )
            if level not in desired_levels:
                continue
            domains = self._extract_domains(section_text[start:end])
            collected.update(domains)
        return collected
