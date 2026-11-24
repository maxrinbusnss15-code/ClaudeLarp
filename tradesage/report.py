from __future__ import annotations

from .models import Decision, Side

COLORS = {Side.LONG: "\033[32m", Side.SHORT: "\033[31m", Side.NO_DECISION: "\033[33m",
          Side.BUY_VOL: "\033[36m", Side.SELL_VOL: "\033[35m"}
RESET, DIM, BOLD = "\033[0m", "\033[2m", "\033[1m"


def render(d: Decision, verbose: bool = False, color: bool = True) -> str:
    c = (lambda s, code: f"{code}{s}{RESET}") if color else (lambda s, code: s)
    lines = [c(f"=== {d.kind.upper()} DECISION: {d.subject} ===", BOLD),
             f"Side: {c(d.side.value, COLORS[d.side])}   score {d.score:+.2f}   conviction {d.conviction:.0%}   "
             f"{c(d.generated_at.strftime('%Y-%m-%d %H:%M UTC'), DIM)}", ""]
    lines.append(c("Questions answered before deciding:", BOLD))
    for a in d.answers:
        mark = c("✔", "\033[32m") if a.answered else c("✘", "\033[31m")
        lines.append(f" {mark} {a.question:<16} {a.text}")
        if verbose:
            lines.append(c(f"     Q: {a.prompt}", DIM))
            for e in a.evidence:
                lines.append(c(f"     - [{e.source} trust {e.trust:.2f}] {e.signal:+.2f} conf {e.confidence:.2f}: "
                               f"{e.summary}", DIM))
    lines += ["", c("Decision:", BOLD)]
    for r in d.rationale[:2]:
        lines.append(f"  {r}")
    lines += ["", c("Action:", BOLD)]
    act = dict(d.action)
    lines.append(f"  {act.pop('instruction', '-')}")
    legs = act.pop("legs", None)
    for k, v in act.items():
        lines.append(f"  {k}: {v}")
    for leg in legs or []:
        lines.append(f"    {leg['action']:<4} {leg['type']:<4} {leg['strike']:>9.2f} {leg['expiry']}  "
                     f"bid {leg['bid']:.2f} ask {leg['ask']:.2f} iv {leg['iv'] or 0:.1%} OI {leg['open_interest']}")
    if d.failures:
        lines += ["", c(f"Sources unavailable ({len(d.failures)}):", "\033[33m")]
        for f in d.failures[: (len(d.failures) if verbose else 5)]:
            lines.append(c(f"  - {f.source}: {f.error}", DIM))
    return "\n".join(lines)
