import json
from unittest.mock import MagicMock, patch

from app.email_pipeline.connectors import imap


def test_xoauth2_payload():
    assert imap._xoauth2_bytes("a@example.com", "token") == b"user=a@example.com\x01auth=Bearer token\x01\x01"


def test_refresh_access_token_posts_refresh_grant():
    response = MagicMock()
    response.read.return_value = json.dumps({"access_token": "short-lived"}).encode()
    response.__enter__.return_value = response
    with patch("urllib.request.urlopen", return_value=response) as opened:
        assert imap._refresh_access_token("client", "secret", "refresh", "https://token") == "short-lived"
    request = opened.call_args.args[0]
    assert request.full_url == "https://token"
    assert b"grant_type=refresh_token" in request.data
    assert b"refresh_token=refresh" in request.data


def test_fetch_uses_xoauth2_when_refresh_credentials_exist():
    client = MagicMock()
    client.search.return_value = ("OK", [b""])
    with patch.object(imap.imaplib, "IMAP4_SSL", return_value=client), patch.object(
        imap, "_refresh_access_token", return_value="access"
    ):
        assert imap._fetch_sync(
            "imap.gmail.com", "a@example.com", "", "INBOX",
            oauth_client_id="client", oauth_client_secret="secret", oauth_refresh_token="refresh",
        ) == []
    client.authenticate.assert_called_once()
    mechanism, callback = client.authenticate.call_args.args
    assert mechanism == "XOAUTH2"
    assert callback(None) == b"user=a@example.com\x01auth=Bearer access\x01\x01"
    client.login.assert_not_called()
