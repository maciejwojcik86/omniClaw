# Nullclaw Runtime Model (How It Works)

## Core Runtime Modes

- `nullclaw agent`: local chat loop (single message or interactive).
- `nullclaw gateway`: long-running runtime for channels + webhook/gateway flow.
- `nullclaw service ...`: install/start/stop/status of background service.
- `nullclaw daemon`: multi-channel daemon runtime path (see CLI reference).

## Core Building Blocks

Nullclaw is built around swappable interfaces (vtable-style) for:
- providers
- channels
- tools
- memory
- runtime adapters
- security/sandbox backends

This means behavior is mostly selected by config, not hardcoded branch logic.

## Security-by-default Runtime Expectations

- Gateway binds locally by default (`127.0.0.1`) unless explicit network/tunnel configuration.
- Pairing is required by default in gateway/web flows.
- Filesystem access is scoped (`workspace_only` behavior).
- Sandbox backend is enabled (`security.sandbox.backend`).

## Operational Commands (high signal)

```bash
nullclaw status
nullclaw doctor
nullclaw channel status
nullclaw gateway
```

## Primary Sources

- https://github.com/nullclaw/nullclaw
- https://github.com/nullclaw/nullclaw/blob/main/README.md
- https://nullclaw.github.io/architecture.html
- https://nullclaw.github.io/cli.html
- https://nullclaw.github.io/security/overview.html
