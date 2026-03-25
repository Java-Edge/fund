import re


def clean_ansi_codes(text):
    if not isinstance(text, str):
        return text
    text = re.sub(r"\033\[\d+(?:;\d+)?m", "", text)
    text = re.sub(r"\[\d+(?:;\d+)?m", "", text)
    return text


def strip_markdown(text: str) -> str:
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"~~(.+?)~~", r"\1", text)
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\|[-:\s|]+\|", "", text)
    text = re.sub(r"\s*\|\s*", " ", text)
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n\n+", "\n\n", text)
    return text.strip()


def format_text(text: str, max_width: int = 60) -> list[str]:
    text = strip_markdown(text)
    lines = []
    text = " ".join(line.strip() for line in text.split("\n") if line.strip())

    current_line = ""
    for char in text:
        current_line += char
        if (char in "。！？；" and len(current_line) > 30) or len(current_line) >= max_width:
            lines.append(current_line.strip())
            current_line = ""

    if current_line.strip():
        lines.append(current_line.strip())

    return lines
