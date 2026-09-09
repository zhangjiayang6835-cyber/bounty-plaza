"""CSS AST parser, tokenizer, and compiler implementation."""

from dataclasses import dataclass
from typing import Dict, List, Optional
import re


@dataclass(frozen=True)
class CssDeclaration:
    """Represents a single CSS property declaration."""

    property_name: str
    property_value: str


@dataclass
class CssRule:
    """Represents a CSS rule set with a selector and map of declarations."""

    selector: str
    declarations: Dict[str, str]

    def get_property(self, name: str) -> Optional[str]:
        """Retrieve declaration value by property name."""
        return self.declarations.get(name.lower().strip())


class CssParser:
    """Parses raw CSS source code into structured CSS rule objects."""

    @staticmethod
    def strip_comments(css_text: str) -> str:
        """Remove CSS block comments from source text."""
        return re.sub(r"/\*[\s\S]*?\*/", "", css_text)

    @classmethod
    def parse_rules(cls, css_text: str) -> List[CssRule]:
        """Parse CSS stylesheet content into a list of CssRule objects."""
        clean_text = cls.strip_comments(css_text)
        pattern = re.compile(r"([^{]+)\{([^}]+)\}")
        rules: List[CssRule] = []

        for match in pattern.finditer(clean_text):
            selector_raw = match.group(1).strip()
            body_raw = match.group(2).strip()
            declarations: Dict[str, str] = {}

            for statement in body_raw.split(";"):
                statement = statement.strip()
                if not statement:
                    continue
                if ":" not in statement:
                    continue
                prop, val = statement.split(":", 1)
                declarations[prop.strip().lower()] = val.strip()

            rules.append(CssRule(selector=selector_raw, declarations=declarations))

        return rules


class CssCompiler:
    """Compiles and minifies CSS source code."""

    def __init__(self, raw_source: str) -> None:
        """Initialize compiler with raw CSS source."""
        self._source = raw_source

    def minify(self) -> str:
        """Minify stylesheet by removing whitespace and redundant semicolons."""
        clean = CssParser.strip_comments(self._source)
        compact_spaces = re.sub(r"\s+", " ", clean)
        compact_delimiters = re.sub(r"\s*([{}:;,])\s*", r"\1", compact_spaces)
        trimmed_semicolons = re.sub(r";\}", "}", compact_delimiters)
        return trimmed_semicolons.strip()

    def get_rules(self) -> List[CssRule]:
        """Parse and retrieve structured CSS rules from compiler source."""
        return CssParser.parse_rules(self._source)

    def find_rule(self, selector: str) -> Optional[CssRule]:
        """Locate rule matching specified selector."""
        target_selector = selector.strip()
        for rule in self.get_rules():
            selectors = [s.strip() for s in rule.selector.split(",")]
            if target_selector in selectors:
                return rule
        return None
