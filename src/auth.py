import requests

_TOKEN_URL = "https://www.warcraftlogs.com/oauth/token"


def get_access_token(client_id: str, client_secret: str) -> str:
    resp = requests.post(
        _TOKEN_URL,
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    if resp.status_code == 401:
        raise ValueError(
            "Invalid WCL credentials. Check your Client ID and Secret at "
            "https://www.warcraftlogs.com/api/clients/"
        )
    resp.raise_for_status()
    return resp.json()["access_token"]
