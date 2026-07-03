import re


def clean_thinking_text(text, output_think_block=False):
    if not isinstance(text, str):
        return "" if text is None else str(text)

    cleaned = text.replace("\r\n", "\n")

    if not output_think_block:
        cleaned = re.sub(
            r"<\|channel\>\s*thought\s*\n?.*?<channel\|>",
            "",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        )
        cleaned = re.sub(
            r"<think\b[^>]*>.*?</think>",
            "",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if re.search(r"</think>", cleaned, flags=re.IGNORECASE):
            cleaned = re.sub(
                r"^.*?</think>\s*",
                "",
                cleaned,
                count=1,
                flags=re.DOTALL | re.IGNORECASE,
            )

    cleaned = re.sub(r"<\|channel\>\s*[\w-]*\s*\n?", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("<channel|>", "")
    cleaned = cleaned.replace("<|think|>", "")
    cleaned = cleaned.replace("<think>", "").replace("</think>", "")
    return cleaned.strip()
