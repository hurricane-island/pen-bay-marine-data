"""
Database utility functions that may be used across multiple CLI tools.
"""
import requests


def create_bucket(host: str, token: str, org: str, database: str, retention: int, timeout: int):
    """
    Args have same name as in Influx DB Client initialization.
    """
    return requests.post(
        f"{host}/api/v2/buckets",
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json"
        },
        json={
            "orgID": org,
            "name": database,
            "retentionRules": [{"type": "expire", "everySeconds": retention}],
        },
        timeout=timeout,
    )