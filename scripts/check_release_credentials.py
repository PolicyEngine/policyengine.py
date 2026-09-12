"""Verify the trusted release job's Hugging Face credential has read-only scope."""

from __future__ import annotations

import os
import sys

import requests


def check_read_only_token(token: str | None) -> None:
    if not token or not token.strip():
        raise ValueError(
            "Full private release verification requires HUGGING_FACE_TOKEN"
        )
    try:
        response = requests.get(
            "https://huggingface.co/api/whoami-v2",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
            allow_redirects=False,
        )
        if response.status_code != 200:
            raise ValueError
        payload = response.json()
        auth = payload.get("auth", {})
        if (
            auth.get("type") != "access_token"
            or auth.get("accessToken", {}).get("role") != "read"
        ):
            raise ValueError
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        # Never include the response, account, token, or request exception in CI
        # output. Unknown and fine-grained permission schemas fail closed.
        raise ValueError(
            "Release verification requires an authenticated Hugging Face access token with role read"
        ) from None


def main() -> int:
    try:
        check_read_only_token(os.environ.get("HUGGING_FACE_TOKEN"))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("Verified read-only Hugging Face release credential")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
