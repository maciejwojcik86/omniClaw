# Setup: Nullclaw Runtime Reference Skill

This setup is optional but recommended when you want reproducible local references.

## 1) Prerequisites

- `git`
- `curl`
- `python3` (optional for parsing)

## 2) Refresh local upstream snapshot (optional)

Run:

```bash
./scripts/refresh_upstream_snapshot.sh
```

This pulls key Nullclaw references into `references/cache/`:
- upstream repo docs (`README.md`, `config.example.json`, `spec/webchannel_v1.json`)
- key examples (`examples/meshrelay`, `examples/modal-matrix`)
- selected docs site pages (`getting-started`, `configuration`, `providers`, `channels`, etc.)

## 3) Security note

Do not copy real API keys/tokens into committed files while creating examples or tests.

## 4) Runtime failures

If runtime smoke commands fail (especially provider/auth failures), use:
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
