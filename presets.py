"""
Shared scenario presets — imported by both `explore.py` (CLI) and
`dashboard.py` (web). Single source of truth for named scenarios.

Each preset carries a CLI slug, a display label (used by both the rich CLI
menu and the dashboard button), a one-line description, and the five
`DiffusionParams` fields.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Preset:
    slug: str               # CLI flag value, lowercase
    display: str            # Emoji + name + parenthetical hint
    desc: str               # One-line description for menus / tooltips
    seed_viewers: int
    population_size: int
    conversation_rate: float
    spread_probability: float
    recovery_rate: float

    def params(self) -> dict:
        """The five DiffusionParams kwargs."""
        return {
            "seed_viewers": self.seed_viewers,
            "population_size": self.population_size,
            "conversation_rate": self.conversation_rate,
            "spread_probability": self.spread_probability,
            "recovery_rate": self.recovery_rate,
        }


PRESETS: list[Preset] = [
    Preset(
        slug="tiny",
        display="🌱 Tiny Creator (10 views)",
        desc="Your friend posts something. 10 people watch it.",
        seed_viewers=10, population_size=500_000,
        conversation_rate=2.0, spread_probability=0.10, recovery_rate=0.08,
    ),
    Preset(
        slug="small",
        display="📺 Small Creator (1K views)",
        desc="A niche channel with a loyal fanbase drops a banger.",
        seed_viewers=1_000, population_size=1_000_000,
        conversation_rate=3.0, spread_probability=0.12, recovery_rate=0.10,
    ),
    Preset(
        slug="mid",
        display="🚀 Mid Creator (10K views)",
        desc="Mid-tier YouTuber, decent algorithm boost.",
        seed_viewers=10_000, population_size=5_000_000,
        conversation_rate=3.5, spread_probability=0.15, recovery_rate=0.10,
    ),
    Preset(
        slug="viral",
        display="🔥 Viral Moment (100K views)",
        desc="Something hits different. The algorithm goes wild.",
        seed_viewers=100_000, population_size=50_000_000,
        conversation_rate=5.0, spread_probability=0.20, recovery_rate=0.12,
    ),
    Preset(
        slug="fizzle",
        display="💨 Fizzle Out (high recovery)",
        desc="Content spreads but people lose interest fast.",
        seed_viewers=500, population_size=1_000_000,
        conversation_rate=2.0, spread_probability=0.10, recovery_rate=0.25,
    ),
    Preset(
        slug="slow_burn",
        display="🕯️ Slow Burn (low conv rate)",
        desc="Word-of-mouth only. No algorithm. Just people talking.",
        seed_viewers=100, population_size=500_000,
        conversation_rate=1.2, spread_probability=0.30, recovery_rate=0.05,
    ),
]

PRESETS_BY_SLUG: dict[str, Preset] = {p.slug: p for p in PRESETS}
