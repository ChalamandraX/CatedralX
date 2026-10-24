"""Encoding utility for display, not encryption or authentication."""
import base64
def encode_text(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")
def decode_text(value: str) -> str:
    return base64.b64decode(value.encode("ascii"), validate=True).decode("utf-8")
