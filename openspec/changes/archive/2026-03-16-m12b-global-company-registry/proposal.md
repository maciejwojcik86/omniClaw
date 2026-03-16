# Proposal: m12b-global-company-registry

## Summary

Replace workspace-local company settings with one global OmniClaw config file at `~/.omniClaw/config.json`. That global file becomes the source of truth for registered companies, their workspace roots, budgets, hierarchy anchors, model catalogs, and runtime settings. The kernel is launched by company reference (`omniclaw --company <slug-or-display-name>`) instead of by manually passing workspace/config paths.

## Why

M11b externalized company workspaces, but the runtime still assumes a workspace-local company config file. That leaves company identity and company configuration fragmented across:

- CLI flags
- environment variables
- workspace-local `config.json`
- workspace-local legacy `company_config.json`

This change unifies company discovery and company configuration into one app-level registry while keeping editable operational text assets in each company workspace.

## What Changes

- Add one host-level OmniClaw config file at `~/.omniClaw/config.json`.
- Resolve company startup by slug or unique display name instead of raw workspace/config path pairing.
- Move company-wide settings ownership into the global registry and remove workspace-local company settings files from normal runtime operation.
- Keep workspaces for editable forms, skills, templates, archives, logs, and per-company SQLite state.

## Goals

- Make `~/.omniClaw/config.json` the canonical company registry and configuration source.
- Start the kernel by company reference rather than raw workspace/config file paths.
- Keep one SQLite DB per company workspace.
- Keep workspaces for editable forms, skills, instruction templates, and runtime artifacts.
- Remove the need for workspace-local company settings files in normal operation.

## Non-Goals

- No shared multi-company database.
- No in-process multi-tenant kernel serving multiple companies simultaneously.
- No change to per-agent Nanobot `config.json` files.

## User-Facing Changes

- New canonical startup:
  - `omniclaw --company <company>`
- New canonical app config:
  - `~/.omniClaw/config.json`
- Company workspaces no longer need their own `config.json` / `company_config.json` for kernel settings.
- Missing workspace paths referenced by the global config cause a startup failure.

## Risks

- Existing scripts/tests currently depend on workspace-local company config files.
- Existing migrated local developer state must be moved into the new global registry cleanly.
- Docs and helper scripts currently mention workspace/config-path startup and must be updated consistently.
