"""Minimal terminal panel."""
import json
from nexus import status
if __name__ == "__main__":
    print(json.dumps(status(), indent=2, ensure_ascii=False))
