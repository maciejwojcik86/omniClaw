from __future__ import annotations

from pathlib import Path

REQUIRED_DIRS: tuple[str, ...] = (
    "inbox/unread",
    "inbox/read",
    "outbox/pending",
    "outbox/drafts",
    "outbox/archive",
    "notes",
    "metrics",
    "drafts",
    "skills",
)

REQUIRED_FILES: dict[str, str] = {
    "notes/DECISIONS.md": "# Decisions\n\n",
    "notes/BLOCKERS.md": "# Blockers\n\n",
    "metrics/KPI.csv": "date,metric,value\n",
    "HEARTBEAT.md": (
        "# HEARTBEAT.md\n\n"
        "- Check `inbox/unread` for new form files.\n"
        "- For each unread message form, run only:\n"
        "  `python3 skills/read_and_acknowledge_internal_message/scripts/acknowledge_and_archive_message.py --apply --workspace-root <this_workspace_root> --form-file <unread_filename>`\n"
        "- Execute these steps immediately without asking for extra confirmation.\n"
        "- Avoid exploratory shell commands unrelated to the skill execution.\n"
        "- The read/ack tool moves `inbox/unread/<file>.md` to `inbox/read/<file>.md` and updates DB form stage.\n"
        "- Keep handled copies out of `inbox/unread`.\n"
        "- If nothing needs attention, reply with `HEARTBEAT_OK`.\n"
    ),
    "AGENTS.md": "# AGENTS\n\nRendered by kernel context injector.\n",
}


def ensure_workspace_tree(*, workspace_root: Path, apply: bool) -> dict[str, tuple[str, ...]]:
    root = workspace_root.expanduser().resolve()

    created_dirs: list[str] = []
    existing_dirs: list[str] = []
    created_files: list[str] = []
    existing_files: list[str] = []

    if root.exists():
        existing_dirs.append(str(root))
    else:
        created_dirs.append(str(root))
        if apply:
            root.mkdir(parents=True, exist_ok=True)

    for relative_dir in REQUIRED_DIRS:
        target = root / relative_dir
        if target.exists():
            existing_dirs.append(str(target))
        else:
            created_dirs.append(str(target))
            if apply:
                target.mkdir(parents=True, exist_ok=True)

    for relative_file, content in REQUIRED_FILES.items():
        target = root / relative_file
        if target.exists():
            existing_files.append(str(target))
        else:
            created_files.append(str(target))
            if apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

    return {
        "created_dirs": tuple(created_dirs),
        "existing_dirs": tuple(existing_dirs),
        "created_files": tuple(created_files),
        "existing_files": tuple(existing_files),
    }
