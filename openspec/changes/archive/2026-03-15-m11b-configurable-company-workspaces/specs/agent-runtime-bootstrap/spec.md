## MODIFIED Requirements

### Requirement: Kernel SHALL Support Human Supervisor Node Registration for Kernel Runner
The kernel SHALL support registering an existing Linux user (the kernel runner) as a HUMAN node with a company-workspace-relative workspace for formal workflow participation.

#### Scenario: Register existing kernel-running user as HUMAN node
- **WHEN** a registration request is submitted for an existing Linux user (for example `macos`)
- **THEN** the kernel upserts a HUMAN node with linux username, company-workspace-relative workspace path, and runtime/config metadata

#### Scenario: Human workspace uses selected company workspace structure
- **WHEN** no explicit human workspace root is provided
- **THEN** the kernel defaults workspace to `<company-workspace-root>/<linux-username>` and scaffolds the standard workspace structure

### Requirement: App Setup SHALL Bootstrap One Human Supervisor Baseline
At application setup, the kernel-running Linux user SHALL be registerable as a HUMAN supervisor node once, with selected company workspace paths and top-agent linkage.

#### Scenario: One-time human supervisor bootstrap
- **WHEN** setup initializes HUMAN node for kernel user (for example `macos`)
- **THEN** node registration is idempotent and workspace scaffold exists under the selected company workspace root

#### Scenario: Top agent linked to human supervisor
- **WHEN** top-level AGENT (for example `Director_01`) is linked to the human supervisor
- **THEN** hierarchy reflects HUMAN -> top AGENT baseline for downstream delegated management
