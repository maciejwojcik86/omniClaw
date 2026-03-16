## ADDED Requirements

### Requirement: OmniClaw Monorepo SHALL Own The Customized Nanobot Runtime Source
The OmniClaw repository SHALL vendor the customized Nanobot runtime source under `third_party/nanobot/` and SHALL use that monorepo path as the authoritative local package source for correctness-critical runtime behavior.

#### Scenario: Local dependency resolution uses vendored runtime
- **WHEN** OmniClaw dependencies are synced from the monorepo
- **THEN** `nanobot-ai` resolves from `third_party/nanobot/`
- **AND** the runtime no longer depends on a separate `/home/macos/nanobot` checkout

### Requirement: Bootstrap Installation SHALL Provide Both CLI Commands From One Shared Environment
The monorepo bootstrap flow SHALL install OmniClaw and Nanobot into one shared environment such that both `omniclaw` and `nanobot` commands are available from that environment.

#### Scenario: Operator bootstraps the monorepo
- **WHEN** the operator runs the canonical bootstrap installer
- **THEN** the shared environment contains an `omniclaw` executable for the kernel package
- **AND** contains a `nanobot` executable for the vendored runtime package
