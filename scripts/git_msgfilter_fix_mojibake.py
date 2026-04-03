"""stdin -> stdout: fix UTF-8 read as Latin-1 in commit messages (Git filter-branch --msg-filter)."""
import sys


def fix_mojibake_line(line: str) -> str:
    if "Ã" not in line and "Â" not in line:
        return line
    try:
        return line.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return line


def fix_mojibake(text: str) -> str:
    if not text:
        return text
    if "Ã" not in text and "Â" not in text:
        return text
    parts = text.splitlines(keepends=True)
    return "".join(fix_mojibake_line(p) for p in parts)


if __name__ == "__main__":
    raw = sys.stdin.buffer.read()
    text = raw.decode("utf-8", errors="replace")
    out = fix_mojibake(text)
    sys.stdout.buffer.write(out.encode("utf-8"))
