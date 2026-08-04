# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Approximate token count for a file or stdin.

Used two ways:
  1. Balancing the two cheatsheets to an EQUAL in-context doc budget (fairness).
  2. The secondary "authored-output tokens" metric — a proxy for boilerplate:
     how much code the agent had to emit to reach a green run.

No network, no heavy deps. If `tiktoken` happens to be installed it is used
(cl100k_base); otherwise a deterministic regex estimate (~word + punctuation
pieces, close enough for *relative* comparison between arms). The number is a
proxy, and reported as one — the harness's headline token figure is the
harness-measured `subagent_tokens`, not this.

    uv run count_tokens.py path/to/file.md
    cat solution.py | uv run count_tokens.py
"""
import re
import sys


def estimate(text: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        # word/number runs + individual punctuation, scaled ~1.3 pieces/word.
        pieces = re.findall(r"\w+|[^\w\s]", text)
        return int(round(len(pieces) * 1.3))


def main() -> int:
    paths = sys.argv[1:]
    if not paths:
        print(estimate(sys.stdin.read()))
        return 0
    total = 0
    for p in paths:
        n = estimate(open(p, encoding="utf-8").read())
        total += n
        print(f"{n:8d}  {p}")
    if len(paths) > 1:
        print(f"{total:8d}  TOTAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
