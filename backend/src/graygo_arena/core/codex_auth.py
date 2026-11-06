"""Read a managed Codex login; delegate token renewal to Codex itself."""

from __future__ import annotations

import base64
import json
import os
import selectors
import subprocess
import time
from pathlib import Path
from threading import Lock
from typing import Any, cast


def read_access_token(path: Path) -> str:
    try:
        data = json.loads(path.read_text())
        token = data.get("tokens", {}).get("access_token")
        if (
            data.get("auth_mode") not in (None, "chatgpt")
            or not isinstance(token, str)
            or not token.startswith("eyJ")
        ):
            raise ValueError("not a managed ChatGPT login")
        return token
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Cannot read the configured Codex ChatGPT login") from exc


def expires_at(token: str) -> float:
    try:
        data = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "==="))
        return float(data["exp"])
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ValueError("Codex ChatGPT access token has no valid expiry") from exc


def refresh_managed_login(binary: str, path: Path) -> None:
    # Auth/account RPC only: no threads, inference turns, shell or MCP tools.
    with subprocess.Popen(
        [binary, "app-server", "--listen", "stdio://"],
        env={**os.environ, "CODEX_HOME": str(path.resolve().parent)},
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    ) as process:
        assert process.stdin is not None and process.stdout is not None
        buffer = b""
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)

                def rpc(identifier: int, method: str, params: dict[str, Any]) -> dict[str, Any]:
                    nonlocal buffer
                    assert process.stdin is not None and process.stdout is not None
                    process.stdin.write(
                        (
                            json.dumps({"id": identifier, "method": method, "params": params})
                            + "\n"
                        ).encode()
                    )
                    process.stdin.flush()
                    deadline = time.monotonic() + 20
                    while time.monotonic() < deadline:
                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                            reply = json.loads(line)
                            if reply.get("id") == identifier:
                                if "error" in reply:
                                    raise ValueError("Codex could not renew the ChatGPT login")
                                return reply.get("result", {})
                        if not selector.select(max(0, deadline - time.monotonic())):
                            break
                        chunk = os.read(process.stdout.fileno(), 65536)
                        if not chunk:
                            break
                        buffer += chunk
                    raise ValueError("Codex ChatGPT login renewal timed out")

                rpc(0, "initialize", {"clientInfo": {"name": "graygo_arena", "version": "0.1.0"}})
                process.stdin.write(b'{"method":"initialized"}\n')
                process.stdin.flush()
                result = rpc(1, "account/read", {"refreshToken": True})
                account = cast(dict[str, Any], result.get("account") or {})
                if account.get("type") != "chatgpt":
                    raise ValueError("Codex has no managed ChatGPT login")
        except (OSError, ValueError) as exc:
            raise ValueError(
                "Cannot renew the Codex ChatGPT login; run codex login on this server"
            ) from exc
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


class CodexOAuthCredentials:
    def __init__(self, path: Path, binary: str) -> None:
        self.path = path
        self.binary = binary
        self.lock = Lock()

    def access_token(self) -> str:
        with self.lock:
            token = read_access_token(self.path)
            if expires_at(token) <= time.time() + 60:
                refresh_managed_login(self.binary, self.path)
                token = read_access_token(self.path)
                if expires_at(token) <= time.time() + 30:
                    raise ValueError("Codex ChatGPT login is expired; run codex login")
            return token
