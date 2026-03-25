import os
import time

from loguru import logger

from app.ai.text_utils import format_text


def save_report(report_dir: str | None, filename_prefix: str, content: str) -> str | None:
    if report_dir is None:
        return None

    if not os.path.exists(report_dir):
        os.makedirs(report_dir, exist_ok=True)

    report_filename = f"{report_dir}/{filename_prefix}{time.strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_filename, "w", encoding="utf-8") as file:
        file.write(content)
    return report_filename


def log_analysis_section(title: str, content: str, *, max_width: int = 60) -> None:
    logger.info(title)
    logger.info("-" * 80)
    for line in format_text(content, max_width=max_width):
        logger.info(line)
