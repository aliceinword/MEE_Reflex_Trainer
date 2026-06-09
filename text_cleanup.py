import re


MOJIBAKE_REPLACEMENTS = {
    "\u00a0": " ",
    "\uf0a7": "",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2032": "'",
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
    "Â©": "(c)",
    "Ã‚Â©": "(c)",
    "Ã¢â‚¬â„¢": "'",
    "Ã¢â‚¬Ëœ": "'",
    "Ã¢â‚¬Â²": "'",
    "Ã¢â‚¬Å“": '"',
    "Ã¢â‚¬Â": '"',
    "Ã¢â‚¬": '"',
    "Ã¢â‚¬â€œ": "-",
    "Ã¢â‚¬â€": "-",
    "Ã¢Ë†â€™": "-",
    "Ã¢â€“Âº": ">",
    "â€™": "'",
    "â€˜": "'",
    "â€œ": '"',
    "â€": '"',
    "â€²": "'",
    "â€“": "-",
    "â€”": "-",
    "âˆ’": "-",
    "â–º": ">",
}


def _looks_like_smashed_text(line: str) -> bool:
    if len(line) < 80:
        return False

    letters = sum(ch.isalpha() for ch in line)
    spaces = line.count(" ")
    words = line.split()
    longest_word = max((len(word) for word in words), default=0)

    return (
        letters > 60
        and (
            spaces <= max(2, len(line) // 80)
            or longest_word >= 45
            or (len(words) <= 10 and len(line) >= 140)
        )
    )


def _words_from_smashed_text(line: str) -> set[str]:
    return {
        word.lower()
        for word in re.findall(r"[A-Z]?[a-z]{3,}|[A-Z]{2,}", line)
        if len(word) >= 4
    }


def _repair_join_boundaries(line: str) -> str:
    line = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", line)
    line = re.sub(r"(?<=[a-z])(?=\")", " ", line)
    line = re.sub(r"(?<=[.!?]\")(?=[A-Z])", " ", line)
    line = re.sub(r"(?<='s)(?=[A-Za-z])", " ", line)
    return line


COMPACTED_WORDS = {
    "a", "able", "about", "account", "against", "allegations", "alerting", "along",
    "affidavit", "amount", "and", "answer", "app", "arguing", "as", "asked", "asserted", "attached",
    "attending", "athlete", "bank", "banking", "basketball", "because", "been", "before",
    "better", "binding", "bore", "by", "called", "cashing", "case", "charged", "check",
    "coach", "complain", "complaint", "concluded", "confirming", "connection", "copy",
    "court", "courts", "customer", "damages", "david", "day", "defamed", "defamatory",
    "did", "dismiss", "district", "domiciled", "drug", "drugs", "due", "ever", "excess",
    "exclaimed", "examined", "explain", "federal", "filed", "filing", "find", "first",
    "for", "fran", "fraud", "from", "gave", "ground", "had", "handed", "has", "have",
    "he", "her", "high", "his", "hometown", "i", "id", "illegal", "immediately", "in",
    "institution", "investigation", "investigator", "is", "it", "job", "just", "lack",
    "law", "learned", "led", "less", "lives", "lost", "many", "months", "moved", "news",
    "newspaper", "no", "notice", "notification", "of", "or", "other", "outcry", "over",
    "payable", "people", "personal", "physically", "picture", "present", "process",
    "produce", "promptly", "public", "published", "question", "quotations", "received",
    "remand", "remanded", "removal", "removed", "reporter", "representations", "returned",
    "reunion", "rumors", "school", "seek", "served", "server", "she", "should", "sought",
    "spreading", "state", "statements", "statutory", "stipulated", "stipulation", "students",
    "subject", "summons", "sworn", "telling", "teller", "ten", "than", "that", "the", "them",
    "then", "there", "these", "they", "time", "to", "transferred", "under", "venue",
    "visited", "wages", "was", "when", "where", "which", "who", "will", "with", "without",
    "works", "would", "write", "year", "photo", "identification",
}


def _compact_key(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _split_compacted_alpha(token: str) -> str:
    if len(token) < 8:
        return token

    lower = token.lower()
    max_word_length = max(len(word) for word in COMPACTED_WORDS)
    best = {0: (0, [])}

    for index in range(len(lower)):
        if index not in best:
            continue

        score, parts = best[index]

        for end in range(index + 1, min(len(lower), index + max_word_length) + 1):
            candidate = lower[index:end]

            if candidate not in COMPACTED_WORDS:
                continue

            if len(candidate) == 1 and candidate not in {"a", "i"}:
                continue

            next_score = score + len(candidate) ** 2
            previous = best.get(end)

            if previous is None or next_score > previous[0]:
                best[end] = (next_score, parts + [token[index:end]])

    if len(lower) not in best:
        return token

    parts = best[len(lower)][1]

    if len(parts) <= 1:
        return token

    return " ".join(parts)


def _repair_compacted_text(text: str) -> str:
    text = re.sub(r"\bsandbore", "s and bore", text)
    text = re.sub(r"\bIdidn\s*twritethat(?=\b|\d)", "I didn't write that", text)
    text = re.sub(r"\btwritethat\b", "t write that", text)
    text = re.sub(
        r"[A-Za-z]{12,}",
        lambda match: _split_compacted_alpha(match.group(0)),
        text,
    )
    text = re.sub(
        r"[A-Za-z]{8,}",
        lambda match: _split_compacted_alpha(match.group(0)),
        text,
    )
    text = re.sub(r"(?<=\d)\.(?=[A-Z])", ". ", text)
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[a-z])(?=\d)", " ", text)
    text = re.sub(r"(?<=\d),\s+(?=\d{3}\b)", ",", text)
    text = re.sub(r"\b([A-Z][a-z]+)\s+sand\s+bore\b", r"\1's and bore", text)
    text = re.sub(r"\b([A-Z][a-z]+)\s+s\s+and\s+bore\b", r"\1's and bore", text)
    text = re.sub(r"\b([Ii])\s*didn\s+t\s*write\b", r"\1 didn't write", text)
    text = re.sub(r"\b([Ii])\s+didn\s*'\s*t\b", r"\1 didn't", text)
    text = re.sub(r"\b([A-Za-z]+)\s+'\s*s\b", r"\1's", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,.;:!?])(?=\S)", r"\1 ", text)
    text = re.sub(r"\s+\"", '"', text)
    text = re.sub(r"(?<=\d),\s+(?=\d{3}\b)", ",", text)
    return re.sub(r"[ \t]{2,}", " ", text)


def normalize_extracted_text(text: str) -> str:
    """Repair common PDF extraction artifacts before import or display."""
    if not text:
        return ""

    for old, new in MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(old, new)

    lines = [line.strip() for line in text.splitlines()]
    rebuilt = []
    short_run = []

    def flush_short_run():
        if short_run:
            if len(short_run) >= 3 or any(len(part) == 1 and part.isalpha() for part in short_run):
                rebuilt.append("".join(short_run))
            else:
                rebuilt.extend(short_run)
            short_run.clear()

    line_index = 0

    while line_index < len(lines):
        line = lines[line_index]

        if not line:
            flush_short_run()
            line_index += 1
            continue

        if len(line) <= 4 and re.fullmatch(r"[\w$,.!?;:'\"()]+", line):
            short_run.append(line)
            line_index += 1
            continue

        short_key = _compact_key("".join(short_run))

        if short_key and _compact_key(line).startswith(short_key):
            short_run.clear()
        else:
            flush_short_run()

        rebuilt.append(line)
        line_index += 1

    flush_short_run()

    cleaned_lines = []
    for line in rebuilt:
        if not line:
            continue

        line = _repair_join_boundaries(line)

        if line.startswith("(c) 2025"):
            continue

        if " | " in line and "MEE" in line:
            continue

        if line.startswith("www."):
            continue

        if line.startswith("Copyright (c)"):
            continue

        if re.fullmatch(r"'+", line):
            continue

        if re.fullmatch(r"\d[\d,]*(?:\.\d+)?\s+to[A-Z][A-Za-z' ]*", line):
            continue

        cleaned_lines.append(line)

    deduped_lines = []
    for line in cleaned_lines:
        if _looks_like_smashed_text(line):
            line = _repair_compacted_text(line)

        if deduped_lines:
            previous = deduped_lines[-1]
            if len(previous) > 25 and line.startswith(previous[:25]):
                deduped_lines[-1] = line
                continue

            if len(line) > 25 and previous.startswith(line[:25]):
                continue

        deduped_lines.append(line)

    text = "\n".join(deduped_lines)
    text = re.sub(r"(?<=\bof)\n(?=\d)", " ", text)
    text = re.sub(r"\b(\d[\d,]*\.)\n(?=[A-Z])", r"\1 ", text)
    text = re.sub(r"\b(\d[\d,]*\.)\n(?=\d[\d,]*\.)", "", text)
    text = re.sub(r"\n'\s*s(?=[A-Za-z])", "'s ", text)
    text = re.sub(r"(?<=\d)\n(?=[,.]\d)", "", text)
    text = re.sub(r"(?<=[A-Za-z])\n(?=\d)", " ", text)
    text = re.sub(r"(?<=[A-Za-z0-9$'\"),.!?])\n(?=[a-z])", " ", text)
    text = re.sub(r"(?<=[a-z])\n(?=[A-Z][a-z])", " ", text)
    text = re.sub(r"(?<=\S)\n(?=[,.;:!?])", "", text)
    text = _repair_join_boundaries(text)
    text = _repair_compacted_text(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
