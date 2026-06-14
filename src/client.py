from typing import Any
import requests

_API_URL = "https://www.warcraftlogs.com/api/v2/client"


def query(token: str, gql: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    resp = requests.post(
        _API_URL,
        json={"query": gql, "variables": variables or {}},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if "errors" in body:
        msgs = "; ".join(e["message"] for e in body["errors"])
        raise RuntimeError(f"GraphQL error: {msgs}")
    return body["data"]
