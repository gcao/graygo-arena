import base64
import json
import time
from pathlib import Path

import pytest

from graygo_arena.core import codex_auth


def write_login(path: Path, expiry: float, account: str = "test") -> str:
    payload = (
        base64.urlsafe_b64encode(json.dumps({"exp": expiry, "account": account}).encode())
        .decode()
        .rstrip("=")
    )
    token = f"eyJhbGciOiJub25lIn0.{payload}.signature"
    path.write_text(json.dumps({"auth_mode": "chatgpt", "tokens": {"access_token": token}}))
    return token


def test_credentials_reread_rotated_login_without_caching_token(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    first = write_login(path, time.time() + 3600)
    credentials = codex_auth.CodexOAuthCredentials(path, "unused-binary")
    assert credentials.access_token() == first
    second = write_login(path, time.time() + 3600, "rotated")
    assert credentials.access_token() == second


def test_expiring_login_is_renewed_by_codex(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "auth.json"
    write_login(path, time.time() - 100)
    calls: list[tuple[str, Path]] = []
    fresh: list[str] = []

    def refresh(binary: str, auth_file: Path) -> None:
        calls.append((binary, auth_file))
        fresh.append(write_login(auth_file, time.time() + 3600))

    monkeypatch.setattr(codex_auth, "refresh_managed_login", refresh)
    credentials = codex_auth.CodexOAuthCredentials(path, "/bin/codex")
    assert credentials.access_token() == fresh[0]
    assert credentials.access_token() == fresh[0]
    assert calls == [("/bin/codex", path)]


def test_failed_renewal_does_not_send_expired_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "auth.json"
    token = write_login(path, time.time() - 100)

    def no_refresh(_binary: str, _path: Path) -> None:
        pass

    monkeypatch.setattr(codex_auth, "refresh_managed_login", no_refresh)
    with pytest.raises(ValueError, match="expired") as error:
        codex_auth.CodexOAuthCredentials(path, "/bin/codex").access_token()
    assert token not in str(error.value)
