"""Screen enum + Navigator. Pure Python, Flet-free, easy to test."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class Screen(str, Enum):
    INTAKE = "intake"
    UPLOAD = "upload"
    EXTRACTED = "extracted"
    COMPLETENESS = "completeness"
    MAPPING = "mapping"
    EXPLAIN = "explain"


SCREEN_ORDER: tuple[Screen, ...] = (
    Screen.INTAKE,
    Screen.UPLOAD,
    Screen.EXTRACTED,
    Screen.COMPLETENESS,
    Screen.MAPPING,
    Screen.EXPLAIN,
)


SCREEN_LABELS: dict[Screen, str] = {
    Screen.INTAKE: "1. Intake",
    Screen.UPLOAD: "2. Upload",
    Screen.EXTRACTED: "3. Confirm Values",
    Screen.COMPLETENESS: "4. Missing Things",
    Screen.MAPPING: "5. VaudTax Mapping",
    Screen.EXPLAIN: "6. Explain",
}


@dataclass
class Navigator:
    current: Screen = Screen.INTAKE
    on_change: Callable[[Screen], None] | None = None
    history: list[Screen] = field(default_factory=list)

    def go(self, target: Screen) -> None:
        if target == self.current:
            return
        self.history.append(self.current)
        self.current = target
        if self.on_change is not None:
            self.on_change(target)

    def next_screen(self) -> Screen | None:
        try:
            idx = SCREEN_ORDER.index(self.current)
        except ValueError:
            return None
        if idx + 1 >= len(SCREEN_ORDER):
            return None
        return SCREEN_ORDER[idx + 1]

    def go_next(self) -> Screen | None:
        nxt = self.next_screen()
        if nxt is not None:
            self.go(nxt)
        return nxt


__all__ = ["Navigator", "Screen", "SCREEN_LABELS", "SCREEN_ORDER"]
