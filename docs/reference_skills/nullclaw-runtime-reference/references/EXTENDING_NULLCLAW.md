# Extending Nullclaw (Providers, Channels, Tools, Skills)

## Extension Strategy

Prefer extension by implementing the target subsystem contract and registering it, instead of editing unrelated runtime code.

## Typical Paths

- New provider: `src/providers/<name>.zig`, register in `src/providers/root.zig`
- New channel: `src/channels/<name>.zig`, register in `src/channels/root.zig`
- New tool: `src/tools/<name>.zig`, register in `src/tools/root.zig`
- Skills: runtime loads skill instructions from workspace skill packs (`~/.nullclaw/workspace/skills/...`)

## Safety Expectations During Extension

- do not weaken default security boundaries while adding capability
- keep tests around failure/boundary paths for security-sensitive changes
- verify behavior with smallest possible runtime command before full daemon/gateway rollout

## Integration Notes For OmniClaw

- OmniClaw should treat Nullclaw as a managed runtime with controlled config injection.
- Keep user-level work inside that user's `~/.nullclaw/workspace`.
- Prefer deterministic bootstrap templates (`AGENTS.md`, TODO notes, persona) before runtime start.

## Primary Sources

- https://github.com/nullclaw/nullclaw/blob/main/AGENTS.md
- https://github.com/nullclaw/nullclaw/blob/main/README.md#architecture
- https://github.com/nullclaw/nullclaw/tree/main/src/providers
- https://github.com/nullclaw/nullclaw/tree/main/src/channels
- https://github.com/nullclaw/nullclaw/tree/main/src/tools
- https://nullclaw.github.io/architecture.html
