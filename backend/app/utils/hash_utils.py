import hashlib


def compute_hash(*parts: str) -> str:
    hasher = hashlib.sha256()
    for part in parts:
        if part is None:
            part = ""
        hasher.update(part.encode("utf-8", errors="ignore"))
    return hasher.hexdigest()
