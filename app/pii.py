from __future__ import annotations

import hashlib
import re

# Order matters: scrub_text applies these sequentially, so longer / more specific
# numeric patterns (16-digit card, 12-digit CCCD) must run BEFORE the 10-digit
# phone pattern, otherwise phone_vn would partially match and mislabel them.
PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "cccd": r"\b\d{12}\b",
    "phone_vn": r"(?:\+84|0)[ \.-]?\d{3}[ \.-]?\d{3}[ \.-]?\d{3,4}",  # 090 123 4567, 090.123.4567, etc.
    "passport": r"\b[A-Z]\d{7,8}\b",  # VN passport: 1 letter + 7-8 digits, e.g. B1234567
    "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "address": r"(?i)\b(?:so nha|đường|duong|phường|phuong|quận|quan|tỉnh|tinh)\b[^,\n]{0,40}",
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
