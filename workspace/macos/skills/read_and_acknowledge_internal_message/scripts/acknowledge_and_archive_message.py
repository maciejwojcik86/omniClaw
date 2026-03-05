#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Acknowledge a message form by moving inbox/unread -> inbox/read, "
            "updating frontmatter stage to ARCHIVED, and posting acknowledge_message_read "
            "to kernel forms endpoint."
        )
    )
    parser.add_argument("--workspace-root", required=True, help="Node workspace root path.")
    parser.add_argument("--form-file", required=True, help="Form filename currently in inbox/unread.")
    parser.add_argument(
        "--actor-node-id",
        default="",
        help="Optional actor node id override.",
    )
    parser.add_argument(
        "--actor-node-name",
        default="",
        help="Optional actor node name override.",
    )
    parser.add_argument(
        "--actor-frontmatter-key",
        default="target",
        help=(
            "Frontmatter key used to infer actor node name when actor args are omitted "
            "(default: target)."
        ),
    )
    parser.add_argument(
        "--kernel-url",
        default="http://127.0.0.1:8000",
        help="Kernel base URL (default: http://127.0.0.1:8000).",
    )
    parser.add_argument(
        "--endpoint",
        default="/v1/forms/actions",
        help="Forms endpoint path (default: /v1/forms/actions).",
    )
    parser.add_argument(
        "--runtime-endpoint",
        default="/v1/runtime/actions",
        help="Runtime endpoint path used for actor fallback lookup (default: /v1/runtime/actions).",
    )
    parser.add_argument(
        "--decision-key",
        default="acknowledge_read",
        help="Decision key for transition (default: acknowledge_read).",
    )
    parser.add_argument(
        "--to-status",
        default="ARCHIVED",
        help="Target status for transition (default: ARCHIVED).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. Dry-run by default.",
    )
    return parser.parse_args()


def parse_frontmatter(raw: str) -> tuple[list[tuple[str, str]], str]:
    if not raw.startswith("---\n"):
        raise ValueError("markdown file is missing YAML frontmatter opening '---'")

    parts = raw.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError("markdown frontmatter is not closed with '---'")

    frontmatter_raw = parts[0][4:]
    body = parts[1]
    if body and not body.startswith("\n"):
        body = "\n" + body

    pairs: list[tuple[str, str]] = []
    for line in frontmatter_raw.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line (expected key: value): {line}")
        key, value = line.split(":", 1)
        pairs.append((key.strip(), value.strip()))
    return pairs, body


def build_frontmatter(pairs: list[tuple[str, str]]) -> str:
    lines = [f"{k}: {v}" for k, v in pairs]
    return "---\n" + "\n".join(lines) + "\n---\n"


def upsert_pair(pairs: list[tuple[str, str]], key: str, value: str) -> None:
    for idx, (k, _) in enumerate(pairs):
        if k == key:
            pairs[idx] = (k, value)
            return
    pairs.append((key, value))


def get_pair_value(pairs: list[tuple[str, str]], key: str) -> str:
    for k, v in pairs:
        if k == key:
            return v
    return ""


def post_transition(
    *,
    kernel_url: str,
    endpoint: str,
    runtime_endpoint: str,
    form_id: str,
    actor_node_id: str | None,
    actor_node_name: str | None,
    decision_key: str,
    to_status: str,
    unread_path: Path,
    read_path: Path,
) -> dict[str, object]:
    url = kernel_url.rstrip("/") + endpoint
    payload = _build_transition_payload(
        form_id=form_id,
        actor_node_id=actor_node_id,
        actor_node_name=actor_node_name,
        decision_key=decision_key,
        to_status=to_status,
        unread_path=unread_path,
        read_path=read_path,
    )
    try:
        return _post_json(url=url, payload=payload, timeout=30)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if (
            exc.code == 422
            and actor_node_name
            and not actor_node_id
            and "actor_node_name" in body
            and "extra_forbidden" in body
        ):
            fallback_actor_node_id = resolve_actor_node_id(
                kernel_url=kernel_url,
                runtime_endpoint=runtime_endpoint,
                actor_node_name=actor_node_name,
            )
            if fallback_actor_node_id:
                retry_payload = _build_transition_payload(
                    form_id=form_id,
                    actor_node_id=fallback_actor_node_id,
                    actor_node_name=None,
                    decision_key=decision_key,
                    to_status=to_status,
                    unread_path=unread_path,
                    read_path=read_path,
                )
                try:
                    return _post_json(url=url, payload=retry_payload, timeout=30)
                except urllib.error.HTTPError as retry_exc:
                    retry_body = retry_exc.read().decode("utf-8", errors="replace")
                    raise RuntimeError(
                        "forms endpoint fallback with actor_node_id failed: "
                        f"HTTP {retry_exc.code}: {retry_body}"
                    ) from retry_exc
                except urllib.error.URLError as retry_exc:
                    raise RuntimeError(f"forms endpoint fallback request failed: {retry_exc}") from retry_exc
        if exc.code == 422 and "actor_node_name" in body and "extra_forbidden" in body:
            raise RuntimeError(
                "forms endpoint rejected actor_node_name (kernel schema is stale). "
                "Restart kernel on latest code or pass --actor-node-id."
            ) from exc
        raise RuntimeError(f"forms endpoint HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"forms endpoint request failed: {exc}") from exc


def _build_transition_payload(
    *,
    form_id: str,
    actor_node_id: str | None,
    actor_node_name: str | None,
    decision_key: str,
    to_status: str,
    unread_path: Path,
    read_path: Path,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "action": "acknowledge_message_read",
        "form_id": form_id,
        "decision_key": decision_key,
        "to_status": to_status,
        "payload": {
            "unread_path": str(unread_path),
            "read_path": str(read_path),
        },
    }
    if actor_node_id:
        payload["actor_node_id"] = actor_node_id
    if actor_node_name:
        payload["actor_node_name"] = actor_node_name
    return payload


def _post_json(*, url: str, payload: dict[str, object], timeout: int) -> dict[str, object]:
    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def resolve_actor_node_id(
    *,
    kernel_url: str,
    runtime_endpoint: str,
    actor_node_name: str,
) -> str | None:
    runtime_url = kernel_url.rstrip("/") + runtime_endpoint
    payload = {"action": "list_agents"}
    try:
        response = _post_json(url=runtime_url, payload=payload, timeout=30)
    except Exception:
        return None

    agents = response.get("agents")
    if not isinstance(agents, list):
        return None
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        raw_name = agent.get("name")
        raw_id = agent.get("id")
        if isinstance(raw_name, str) and isinstance(raw_id, str) and raw_name == actor_node_name and raw_id:
            return raw_id
    return None


def ensure_kernel_reachable(*, kernel_url: str) -> None:
    healthz_url = kernel_url.rstrip("/") + "/healthz"
    req = urllib.request.Request(url=healthz_url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                raise RuntimeError(f"kernel health check returned HTTP {resp.status}")
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"kernel is unreachable at {healthz_url}; start kernel and retry ({exc})"
        ) from exc


def main() -> int:
    args = parse_args()

    workspace_root = Path(args.workspace_root).expanduser().resolve()
    unread_path = workspace_root / "inbox" / "unread" / args.form_file
    read_dir = workspace_root / "inbox" / "read"
    read_path = read_dir / args.form_file

    if not unread_path.exists():
        if read_path.exists():
            existing_content = read_path.read_text(encoding="utf-8")
            existing_pairs, _ = parse_frontmatter(existing_content)
            existing_stage = get_pair_value(existing_pairs, "stage")
            if existing_stage == args.to_status:
                print(
                    json.dumps(
                        {
                            "status": "already_acknowledged",
                            "form_id": get_pair_value(existing_pairs, "form_id") or Path(args.form_file).stem,
                            "read_path": str(read_path),
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 0

        print(f"Unread form file not found: {unread_path}", file=sys.stderr)
        return 1

    original_content = unread_path.read_text(encoding="utf-8")
    pairs, body = parse_frontmatter(original_content)

    form_type = next((v for k, v in pairs if k == "form_type"), "")
    if form_type != "message":
        print(f"Expected form_type=message, got '{form_type}'", file=sys.stderr)
        return 1

    form_id = get_pair_value(pairs, "form_id")
    if not form_id:
        form_id = Path(args.form_file).stem
        upsert_pair(pairs, "form_id", form_id)

    upsert_pair(pairs, "stage", args.to_status)
    upsert_pair(pairs, "transition", args.decision_key)
    patched_content = build_frontmatter(pairs) + body.lstrip("\n")

    actor_node_id = args.actor_node_id.strip() or None
    actor_node_name = args.actor_node_name.strip() or None
    if not actor_node_id and not actor_node_name:
        actor_key = args.actor_frontmatter_key.strip()
        if actor_key:
            inferred = next((v for k, v in pairs if k == actor_key), "").strip()
            if inferred and inferred.lower() not in {"none", "null", "{{none}}"}:
                actor_node_name = inferred
    if not actor_node_id and not actor_node_name:
        print(
            "Unable to resolve actor node identity; pass --actor-node-id or --actor-node-name.",
            file=sys.stderr,
        )
        return 1

    dry_payload = {
        "workspace_root": str(workspace_root),
        "unread_path": str(unread_path),
        "read_path": str(read_path),
        "form_id": form_id,
        "actor_node_id": actor_node_id,
        "actor_node_name": actor_node_name,
        "decision_key": args.decision_key,
        "to_status": args.to_status,
    }
    if not args.apply:
        print("DRY-RUN")
        print(json.dumps(dry_payload, indent=2, sort_keys=True))
        return 0

    try:
        ensure_kernel_reachable(kernel_url=args.kernel_url)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    moved = False
    try:
        read_dir.mkdir(parents=True, exist_ok=True)

        shutil.move(str(unread_path), str(read_path))
        moved = True
        read_path.write_text(patched_content, encoding="utf-8")

        response = post_transition(
            kernel_url=args.kernel_url,
            endpoint=args.endpoint,
            runtime_endpoint=args.runtime_endpoint,
            form_id=form_id,
            actor_node_id=actor_node_id,
            actor_node_name=actor_node_name,
            decision_key=args.decision_key,
            to_status=args.to_status,
            unread_path=unread_path,
            read_path=read_path,
        )
    except Exception as exc:
        if moved and read_path.exists():
            try:
                read_path.write_text(original_content, encoding="utf-8")
                shutil.move(str(read_path), str(unread_path))
            except OSError:
                pass
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "form_id": form_id,
                "read_path": str(read_path),
                "endpoint_action": response.get("action"),
                "new_status": (response.get("form") or {}).get("current_status"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
