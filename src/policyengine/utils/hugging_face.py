import os
import json
from urllib import request


def hf_list_tags(repo: str) -> list[str]:
    """Return tag names for a Hugging Face repo.

    Tries huggingface_hub first (dataset repo), then model; falls back to HTTP
    calls against both endpoints. Uses HUGGING_FACE_TOKEN if present.
    """
    token = os.getenv("HUGGING_FACE_TOKEN")

    def _filter_sort_versions(ts: list[str]) -> list[str]:
        """Keep only tags like a.b.c (optionally prefixed with 'v'), sort ascending."""
        clean: list[tuple[str, tuple[int, int, int]]] = []
        for t in ts:
            if not isinstance(t, str):
                continue
            s = t.strip()
            if s.startswith("v"):
                core = s[1:]
            else:
                core = s
            parts = core.split(".")
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                continue
            try:
                key = (int(parts[0]), int(parts[1]), int(parts[2]))
            except Exception:
                continue
            clean.append((t, key))
        clean.sort(key=lambda x: x[1])  # ascending sequential order
        return [t for t, _ in clean]

    # 1) huggingface_hub API
    try:
        from huggingface_hub import HfApi  # type: ignore

        api = HfApi(token=token)
        # Try as dataset repo
        refs = api.list_repo_refs(repo, repo_type="dataset")
        tags = [t.name for t in (refs.tags or [])]
        tags = _filter_sort_versions(tags)
        if tags:
            return tags
        # Try as model repo (fallback)
        refs = api.list_repo_refs(repo, repo_type="model")
        tags = [t.name for t in (refs.tags or [])]
        tags = _filter_sort_versions(tags)
        if tags:
            return tags
    except Exception:
        pass

    # 2) HTTP fallback: try both endpoints
    def _http_tags(endpoint: str) -> list[str]:
        url = f"https://huggingface.co/api/{endpoint}/{repo}/refs?type=tag"
        req = request.Request(url)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return []
        tags: list[str] = []
        if isinstance(data, dict):
            if isinstance(data.get("tags"), list):
                tags = [
                    t.get("name")
                    for t in data.get("tags", [])
                    if t.get("name")
                ]
            elif isinstance(data.get("refs"), dict) and isinstance(
                data["refs"].get("tags"), list
            ):
                tags = [
                    t.get("name")
                    for t in data["refs"].get("tags", [])
                    if t.get("name")
                ]
            elif isinstance(data.get("refs"), list):
                tags = [
                    r.get("name")
                    for r in data.get("refs", [])
                    if r and r.get("name") and r.get("type") == "tag"
                ]
        return tags

    for endpoint in ("datasets", "models"):
        tags = _http_tags(endpoint)
        tags = _filter_sort_versions(tags)
        if tags:
            return tags

    return []
