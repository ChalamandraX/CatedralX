"""Placeholder security response; does not mislead or modify external traffic."""
def inspect_request(metadata: dict) -> dict:
    suspicious = bool(metadata.get("suspicious", False))
    return {"suspicious": suspicious, "action": "flag_for_review" if suspicious else "allow_local_processing",
            "obfuscation_enabled": False}
