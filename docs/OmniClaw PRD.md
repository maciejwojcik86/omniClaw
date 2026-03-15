# **OmniClaw**

**Master Product Requirements Document (PRD) & Development Roadmap**

**Version:** 2.1

**Target Hardware:** Any Linux Instance (Ubuntu preferred)

**Core Tech Stack:** Linux, Nullclaw (Zig/Node), SQLite/PostgreSQL, FastAPI/Go/Rust (Kernel), LiteLLM (Proxy)

## **1\. Executive Summary & Vision**

The goal of this project is to build an Operating System ("OmniClaw" or "The Kernel") that orchestrates a self-organizing, self-improving Hierarchical Multi-Agent System of OpenClaw like agents.

Unlike traditional multi-agent frameworks that run multiple agents within a single process and share memory, OmniClaw OS enforces strict OS-level isolation. Each agent operates as a distinct Linux user, utilizing the lightweight Nullclaw framework. The agents are fundamentally untrusted and restricted.

**Core Paradigm Shifts:**

1. **Forms over Chat:** Agents do not just "chat"; they submit formal, stateful Markdown/YAML forms tracked by the Kernel's database. They may send informal messages via telegram channels or irc as further implementation, but company operates via formal md files with yaml frontmatter metadata  
2. **Waterfall Budgeting:** Fiat budget is injected at the top (CEO) and explicitly allocated downward as percentages, ensuring total cost control.  
3. **Template Injection:** Agents are fed real-time situational awareness (time, cost of last task, remaining budget, team structure) via Kernel-rendered prompt templates of AGENTS.md, giving them temporal consistency and fresh context everytime they wake up.  
4. **Master Skill Lifecycle:** Agent Skill.md format will serve as Tools and SOPs for agents, they should be validated, version-controlled, and centrally distributed by the Kernel.

**Core Maxim:** Authority, trust, and budgets flow *top-down*; autonomy, proposals, and initiative flow *bottom-up*.

To achieve complex, AGI-like autonomous behavior, the system relies on an overarching orchestration App (The Kernel) that acts as the "Laws of Physics." It handles security, file routing, budgets, and state. The agents provide the "Corporate Culture"—reasoning, execution, and continuous improvement driven by layered Markdown prompts, real-time templated state injection, and rigid note-keeping habits.

Furthermore, the system integrates Pharmaceutical Good Manufacturing Practice (GMP) principles alongside advanced Corporate Coordination systems (OKRs, Internal Economies, Matrix Task Forces). It does not rely on agents to "be smart"; it relies on a fault-tolerant, perfectly aligned system architecture to catch errors and coordinate massive parallel efforts.

## **2\. Core Architectural Philosophy: The Rigid vs. The Soft**

The most critical design pattern of OmniClaw OS is the absolute **Separation of Concerns** between the Hardcoded System (Kernel) and the Prompt-Driven System (Agent Space).

### **2.1 The Rigid Domain (OmniClaw Kernel)**

The Kernel is the backend daemon/API running as a privileged Linux service (root or sudoers equivalent). It is completely agnostic to the actual work the agents are doing.

The Kernel is a lightweight, privileged background daemon. It is the central ERP (Enterprise Resource Planning) system.

* **State Machine:** It tracks the status of formal requests (e.g., draft → in\_qa → approved) in its SQL database.  
* **Master Skill Distributor:** It copies approved scripts from the Master\_Skills vault into the workspaces of authorized agents.  
* **Context Injector:** It dynamically compiles AGENTS.md by replacing {{variables}} with live DB data.  
* **Permission Enforcer:** It provisions Linux users. Managers are granted chmod/chown read/write access to their subordinates' directories.

* **Enforces Isolation:** Agents cannot cd into another agent's directory. They cannot chmod files.  
* **Manages State:** Holds the single source of truth in an SQL database (Org Chart, Budgets, Quotas, Skills).  
* **Inter-Process Communication (IPC):** Agents communicate exclusively via Markdown files. The Kernel acts as a daemon, monitoring outboxes, validating hierarchy permissions, and securely routing files to target inboxes.  
* **Approval Gates:** Manages state machines for human/CEO approvals (e.g., Budget Requests, Skill Deployments).

### **2.2 The Soft Domain (Aegis Swarm)**

The Swarm is the intelligence. It is highly fluid and defined entirely by plain text.

* **Dynamic Reorganization:** Roles and Hierarchies are not hardcoded. A "Dev Team" is simply a Manager Agent with Subordinate Agents.  
* **Context Stacking & Templating:** Agent behavior is dictated by stacking company\_constitution.md (universal game rules), team\_mandate.md (scope/SLAs), and a highly dynamic, templated AGENTS.md (specific role and live state).  
* **Policy-Driven Autonomy:** Agents can execute tasks independently, but any structural change (new tools, prompt edits, new workflows) requires submitting a formal **Proposal** to their manager.  
* **Self-Healing:** Manager/HR agents actively rewrite the instruction templates of underperforming worker agents to permanently alter their behavior (CAPA).
* **Managerial Supervision:** Managers proactively cd into their workers' workspaces, review their drafts, audit their spending, and edit their persona\_template.md files to improve performance.  
* **Process Skills:** Agents are given specific SOP Skills explaining *how* to fill out a Form (e.g., "How to request a new subordinate," "How to request a budget increase").

## **3\. The Agent Workspace & Behavioral Habits**

A key to preventing "hallucination loops" is enforcing strict **note-keeping discipline**. Agents must externalize their state; they are forbidden to "just remember" things in their LLM context window.

### **3.1 The Standard Linux Workspace**

When the Kernel spawns a new Agent, it generates this strict directory structure:  
`/home/agent_xyz/workspace/`  
 `├─ inbox/new/            (Kernel drops incoming routed Forms here)`  
 `├─ inbox/read/`             
 `├─ outbox/send/       (Agent saves Forms here for Kernel routing)`  
 `├─ outbox/sent/`            
 `├─ notes/TODO.md         (Single owner task list: priority, due, status)`  
 `├─ notes/DECISIONS.md    (Append-only decision log: when/why/approved by)`  
 `├─ notes/BLOCKERS.md     (Current obstacles + requested help)`  
 `├─ refs/INDEX.yaml       (Links to datasets, tools, APIs, and scopes)`  
 `├─ journal/DAILY.md      (Short run log + self-reflection)`  
 `├─ drafts/               (WIP code/outputs before QA submission)`  
 `├─ skills/               (Read-only. Kernel syncs approved tools here)`  
 `├─ persona_template.md   (Authored by Manager, contains {{variables}})`  
 `└─ AGENTS.md             (Read-only final prompt, auto-rendered by Context Injector)`

### **3.2 Core Behavioral Traits (Enforced via Prompt Scaffold)**

Every agent's dynamic system prompt includes hooks to these files:

* **Self-Reflection:** After each task, the agent writes a short retro in its DAILY.md (what worked, what didn't, how to do it cheaper/faster next time).  
* **Budget Awareness:** Before executing a plan, the agent must estimate the token/cost and verify it fits the daily budget. If funds are tight, it downgrades its strategy.  
* **Manager-First Escalation:** If blocked or over budget, the agent halts and writes to BLOCKERS.md, then routes a message to its manager with: *Problem → Attempted → Options w/ cost → Ask*.  
* **Reproducibility:** Agents must log inputs, tools used, and links to artifacts so QA/Audit agents can replay the work.

### **3.3 Agent KPIs & Self-Metrics (KPI.csv)**

Workers are evaluated on:

1. **Task success rate** (rolling 7/30 runs)  
2. **Cost per successful task** (tokens or £)  
3. **Cycle time** (create → done)  
4. **Doc hygiene score** (Did it update TODOs and Journals?)  
5. **Escalation latency** (time from blocker → asking for help)


### **3.4 The Graph Routing Engine  (Stateful Forms)**

Agents communicate using standardized Markdown files with strict YAML frontmatter. The Kernel parses this frontmatter, updates the database state, and routes the form.

Instead of hardcoding tables for every request, the DB contains a form_schemas table storing routing logic as a Directed Graph.

* **Form Objects:** Agents use specific SOPs to fill out YAML frontmatter on Markdown files (e.g., Type: Proposal, Action: submit_for_review).  
* **Graph Traversal:** The Kernel reads the graph for that form_type, identifies the current stage, maps the action edge to the next stage, resolves the target agent (e.g., {{initiator}}), and physically moves the file.


### **3.5 Dynamic Prompt Templating (Context Injection)**

The Kernel runs a daemon that reconstructs AGENTS.md before an agent wakes.

**Variables Injected:**

* {{current\_time\_utc}}  
* {{company\_announcements}} (Broadcasted from Director)  
* {{line\_manager\_id}}  
* {{subordinates\_list}}  
* {{current\_budget\_allowance}} & {{current\_budget\_spent}}  
* {{last\_5\_conversations\_summary}} & {{cost\_of\_last\_run}}

### **3.6 Master Skill Library & Validation Lifecycle**

Skills (Python scripts, shell scripts, SOP markdowns) are version-controlled in a secure root folder.

* **Validation States:** Draft → Testing → Approved → Deprecated.  
* **Deployment:** When a QA agent signs off and a Manager approves, the DB state flips to Approved. The Kernel automatically copies v1.2 of the script into the /skills/ folder of every agent mapped to that skill in the database.

## **4\. Corporate Coordination Mechanisms**

Real companies use macro-systems to align thousands of independent actors. OmniClaw translates these mechanisms into agentic workflows.

### **4.1 Strategic Alignment: Objectives & Key Results (OKRs)**

* **Concept:** Agents must know how to prioritize competing tasks in their TODO.md.  
* **Implementation:** The Board/Director authors a company\_okrs.md file. The Kernel injects a read-only copy into every Manager's workspace. Managers translate this into a team\_okrs.md file injected into their Workers' workspaces. When a Worker agent is faced with 5 tasks, its prompt instructs it to evaluate which task most directly impacts the active OKRs and execute that first.

### **4.2 Matrix Management: Task Forces (War Rooms)**

* **Concept:** Strict hierarchies create silos. Complex goals require cross-functional collaboration.  
* **Implementation:** A Manager requests a "Task Force" via the Kernel. The Kernel provisions a temporary, shared Linux directory (e.g., /var/taskforces/project\_alpha/). It grants read/write permissions to specific agents across different departments (e.g., a Dev, a Marketer, a QA). These agents collaborate laterally in this shared space while retaining their primary reporting lines, disbanding the workspace when the project concludes.

### **4.3 Waterfall Budget Control**

The human funds the master LiteLLM proxy with a daily allowance (e.g., $50/day).

* **The Cascade:** The Board Node holds 100% ($50). It allocates 40% ($20) to the Dev Dept, 20% ($10) to Marketing. The Dev Manager allocates 50% of its pool to Worker A, 40% to Worker B, keeping 10% for its own managerial tasks.  
* **Running Dry:** If a worker exhausts its quota, it uses the "Budget Request Skill" to submit a Form to its manager.  
* **Managerial Action:** The manager can approve the form (allocating from its reserves), reject it, or rewrite the worker's persona\_template.md to force it to use a cheaper, quantized model.

### **4.4 Internal Economy: Cross-Charge Budgets**

* **Concept:** Departments should not drain their own budgets fulfilling requests from other departments. Supply and demand should dictate resource allocation.  
* **Implementation:** If the Marketing Agent requests a custom script from the Dev Team, the email request includes a budget\_transfer\_auth in the YAML frontmatter. The Kernel deducts $2.00 from Marketing's LiteLLM quota and credits it to the Dev Team to "fund" the compute required to build the tool.

### **4.5 Retrospective Internal Audit**

* **Concept:** Inline QA prevents errors today, but who ensures QA isn't hallucinating?  
* **Implementation:** A specialized "Internal Audit" Agent operates outside the standard hierarchy, reporting directly to the Board/Director. It randomly samples completed tasks and approved QA logs across the company. If it finds a false-positive approval, it issues a penalizing CAPA not to the worker, but to the QA Agent and its Manager.

## **5\. Adapting Pharmaceutical GMP to AI Swarms**

To prevent the swarm from generating cascading failures, OmniClaw implements "Embedded Quality".

### **5.1 Separation of Duties (Maker / Checker)**

* **Concept:** The entity that creates a product cannot be the entity that approves or deploys it.  
* **Implementation:** A "Coder Agent" never has permission to write a file to a Production folder. It can only write to /drafts/. A separate "QA Agent" must review the draft, run tests, and submit a payload to the Kernel to move the file.

### **5.2 CAPA (Corrective and Preventive Action)**

* **Concept:** When a failure occurs, fix the immediate problem (Corrective), then alter the system to ensure it never happens again (Preventive).  
* **Implementation:** 1\. Worker fails a task. Manager kicks back the task. 2\. Manager identifies root cause. 3\. Manager/HR updates the worker's persona\_template.md, appending a new strict SOP (e.g., "ALWAYS verify JSON schema before closing files"). The Kernel re-renders AGENTS.md and hot-reloads the worker.

### **5.3 Skill Validation Pipeline (IQ / OQ / PQ)**

Tools and external API calls are treated as "Skills". Before a new script becomes an available Skill, it undergoes:

* **Installation Qualification (IQ):** Kernel verifies the script has no malicious OS commands and installs dependencies in a sandbox.  
* **Operational Qualification (OQ):** QA Agent runs unit tests against the script.  
* **Performance Qualification (PQ):** The script is run in a staging environment by a worker on dummy data.  
* *Only upon passing all three does the Manager/Board approve the Skill for deployment.*

## **6\. Technical Specifications: The OmniClaw Kernel**

### **6.1 System Infrastructure**

* **OS:** Any Linux Server OS (Debian/Ubuntu recommended).  
* **Agent Runtime:** Nullclaw wrapped in a systemd service for each agent user.  
* **Proxy:** LiteLLM running locally. LiteLLM handles API key translation, load balancing to cloud models, and enforces the daily token/cost budgets assigned by the Kernel.

### **6.2 Database Schema (The Canonical State)**

The Kernel requires a relational database (SQLite/PostgreSQL) to act as the ultimate source of truth.

**Table: nodes** (Agents & Humans)

* id (UUID, Primary Key)  
* type (Enum: 'AGENT', 'HUMAN')  
* name (String)  
* linux\_uid (Integer, null for humans)  
* autonomy\_level (Integer: 0=Read-only, 1=Probation, 2=Active, 3=Can Propose Tool Changes)  
* status (Enum: 'DRAFT', 'PROBATION', 'ACTIVE', 'PAUSED', 'RETIRED')

**Table: hierarchy** (The Org Chart)

* id (UUID)  
* parent\_node\_id (UUID)  
* child\_node\_id (UUID)  
* relationship\_type (Enum: 'MANAGES')

**Table: budgets** (Financial Quotas via LiteLLM)

* id (UUID)  
* node\_id (UUID)  
* daily\_limit\_usd (Decimal)  
* per\_task\_cap\_usd (Decimal)  
* virtual\_api\_key (String, maps to LiteLLM)
* parent\_node\_id (FKey)  
* allocated\_percentage (Decimal)  
* current\_daily\_allowance (Decimal calculated)  
* current\_spend (Decimal)

**Table: form\_schemas**

* form\_type (e.g., 'spawn\_agent', 'budget\_rebalance', 'deviation')  
* graph\_json (Defines stages, required\_skills, and decision edges).

**Table: forms\_ledger** (State Machine)

* form\_id (String, e.g., 'REQ-001')  
* type (Enum: 'BUDGET', 'SPAWN\_AGENT', 'SKILL\_DEPLOY', 'TASK\_DELEGATION')  
* current\_status (Enum: 'DRAFT', 'SUBMITTED', 'IN\_REVIEW', 'RETURNED', 'APPROVED')  
* current\_holder\_node (UUID \- Who currently has the file in their inbox)  
* history\_log (JSON Array of timestamps and state changes)

**Table:  master\_skills** (Validated Tools/SOPs)

* id (UUID)  
* name (String)  
* execution\_endpoint (String)  
* validation\_status (Enum: 'DRAFT', 'IN\_QA', 'VALIDATED')

### **6.3 Core Kernel Processes (The Hardcoded Rules)**

#### **A. The Form State Daemon**

Agents communicate exclusively via a hybrid file-system approach.
Runs every 5 seconds. Scans all /outbox/send/ folders.

* Parses YAML frontmatter.  
* Updates forms\_ledger in the DB.  
* If status \== approved on a form, it triggers the function (e.g. spawn new user and set up nullclaw, or run other scripts)  
* Moves the physical .md file to the target's /inbox/new/ folder (and move sender copy to 'sent' subfolder)

Simple eform example
* **Sending Mail:** An agent creates a .md file in /workspace/outbox/send/ with YAML frontmatter.  
* **Kernel Routing:** The Kernel daemon detects the file, reads the frontmatter, verifies the sender has permission to message the target, executes budget transfers if present, and securely copies the file to the target's /inbox/new/. 
* **Receiving Mail (Heartbeat):** Each Nullclaw agent has a heartbeat.md file that triggers on wake. It checks /inbox/new/, processes the contents, and moves the email to /inbox/read/.
Alternatively we can use claw agent Hearthbeat.md to prompt it to read and act on new unread files in the inbox




#### **B. Context Injector Daemon (Dynamic Prompt Templating)**
Runs prior to Nullclaw execution. Queries the budgets table and LiteLLM logs. Parses /persona\_template.md, replaces all {{variables}}, and overwrites AGENTS.md as read-only.

* **Purpose:** Provides agents with real-time state awareness and situational control without requiring LLM calls to fetch basic environment data.  
* **Implementation:** Agents do not edit their own core system instructions. Instead, HR agents draft a persona\_template.md containing placeholders (e.g., {{current\_time}}, {{budget\_remaining}}, {{subordinates}}, {{active\_okrs}}, {{company\_announcements}}).  
* **Kernel Action:** A continuous background process monitors the database and the templates. It parses persona\_template.md, replaces all {{variables}} with actual live values from the DB, and renders the final, read-only AGENTS.md file into the workspace. Nullclaw loads AGENTS.md directly into the system prompt on every execution.


#### **C. The Budget Sync Daemon**

Runs daily at 00:00 UTC. Resets all current\_spend to 0\. Recalculates current\_daily\_allowance based on the overarching Human allocation and the hierarchy percentages.


#### **D. Provisioning API (Master Tools)**

POST /api/v1/kernel/nodes/spawn

* **Purpose:** Requests the creation of a new Linux user and subordinate agent workspace.  
* **Kernel Action:** Checks if the requesting Node has Manager privileges. Runs Linux useradd, generates the workspace, drops the initial persona\_template.md, renders AGENTS.md, and starts the Nullclaw systemd service.

#### **E. Request & Approval API**

POST /api/v1/kernel/requests/submit

* **Purpose:** For structural changes (Proposals for new Tools, Workflow tweaks, Task Force creation).  
* **Kernel Action:** Places request in PENDING state. Routes a notification to the superior Manager's inbox (or Human).

#### **F. Instruction Update API (CAPA enforcement)**

PUT /api/v1/kernel/instructions/update\_template

* **Purpose:** Allows Managers/HR to rewrite the instruction templates of a subordinate.  
* **Kernel Action:** Overwrites the target's persona\_template.md. The Context Injector instantly detects the change, rebuilds AGENTS.md, and triggers a systemctl restart nullclaw\_agent\_xyz.

## **7\. The Human-in-the-Loop (Nodes Anywhere)**

Humans are treated as standard nodes in the hierarchy, meaning they can exist anywhere in the Org Chart.

* **Top-Level (The Board):** Agent\_000 (The Director) reports directly to Human\_01. The human sets the overarching strategy and funds the company.  
* **Mid-Level (Targeted QA):** A Human Node can be placed underneath a specific Dev Manager Agent for critical HITL approvals inside a workflow without escalating to the very top.  
* **The Config Dashboard:** A lightweight web UI served by the Kernel to allow humans to view the Org Chart, adjust auto-approval thresholds, and hit a master "Kill Switch" to stop all Nullclaw services.

## **8\. Hypothetical Corporate Workflows (For AI Developer Context)**

### **8.1 Genesis: Bootstrapping the Minimal Org**

1. Human runs the genesis script.  
2. Kernel creates **Agent\_000 (Director)** and hands it goals.  
3. Director evaluates goals and autonomously uses /spawn to create the minimal 4 seeds:  
   * **HR Head:** Owns agent lifecycle, skills matrix, and drafting persona\_template.md files for new hires.  
   * **Platform Head:** Owns repos, tool registry, runtime flags.  
   * **Finance Head:** Owns daily budget allocations and cost forecasts.  
   * **Governance/QA Head:** Owns compliance checks and internal audit.

### **8.2 The HR Function: Instruction Drafting & Templating**

1. **Goal:** The company needs a Data Entry Agent.  
2. **Drafting:** An HR Agent creates a new persona\_template.md file tailored to Data Entry. It intentionally includes variables: *"You report to {{manager\_name}}. Your remaining daily budget is ${{budget\_remaining}}."*  
3. **Approval:** The HR Manager approves the template.  
4. **Deployment:** The HR Manager calls the Kernel to spawn the agent. The Context Injector immediately renders the final AGENTS.md with the true names and dollar amounts.

### **8.3 Matrix Collaboration: The War Room**

1. Director identifies a complex goal requiring a new web app and a marketing campaign.  
2. Director calls the Kernel to spawn a **Task Force** workspace (/var/taskforces/project\_omega/).  
3. The Kernel grants read/write access to Dev\_Agent\_01, Design\_Agent, and Marketing\_Agent.  
4. The agents operate concurrently in the shared folder, leaving notes in a shared decisions.md file, while still sending their daily status reports back to their respective permanent Managers.

## **9\. Master Development Roadmap**

This roadmap is designed for an AI Coding Agent (e.g., Claude Code) to execute iteratively.

### **Phase 1: The Foundation (Kernel OS & DB)**

**Goal:** Establish the rigid laws of physics. No AI logic yet.

* \[ \] Set up generic Linux environment.  
* \[ \] Initialize the SQLite/PostgreSQL database.  
* \[ \] Build the core backend App (FastAPI/Go/Rust).  
* \[ \] Implement Linux OS interactions: Scripts to run useradd, generate keys, and set up the exact workspace directory structure (inbox, outbox, notes, drafts, AGENTS.md).  
* *Definition of Done:* Backend can receive an API call, create a new Linux user with the correct folders, and log it in the DB.

### **Phase 2: Communications Daemon & Context Injector**

**Goal:** Allow entities to talk, spend money safely, and be aware of their state.

* \[ \] Install/configure LiteLLM as a local proxy. Connect it to the Kernel's DB to manage virtual keys and quotas.  
* \[ \] Build the IPC File Routing Daemon.  
* \[ \] Build the Context Injector Daemon: Parses persona\_template.md, pulls variables from SQLite, and renders AGENTS.md.  
* *Definition of Done:* User A receives mail in their inbox, and their AGENTS.md automatically updates to show {{budget\_remaining}} dropped by the cost of the transaction.

### **Phase 3: The Genesis Boot (Integrating Nullclaw)**

**Goal:** Bring the first agent online.

* \[ \] Install Nullclaw framework.  
* \[ \] Create the systemd wrapper template.  
* \[ \] Implement the Context Stacking logic (combining Constitution \+ OKRs \+ AGENTS.md).  
* \[ \] Implement the Heartbeat cycle logic in Nullclaw to process /inbox/new/ and update TODO.md.  
* \[ \] Spawn Agent\_000 (The Director) and Human\_01.  
* *Definition of Done:* Human sends a webhook message that drops a .md file into the Director's inbox; Director wakes up, reads it, logs it in DECISIONS.md, and routes a response back.

### **Phase 4: Expansion & HR Governance**

**Goal:** Enable the Director to build the company.

* \[ \] Implement the nodes/spawn endpoint.  
* \[ \] Implement the instructions/update\_template endpoint for HR to push CAPAs.  
* *Definition of Done:* Director receives a goal, autonomously spawns the HR Manager, sets a budget, and the HR Manager successfully boots up in Probation status.

### **Phase 5: Advanced Corporate Coordination**

**Goal:** Implement Task Forces, Audits, and Maker/Checker loops.

* \[ \] Implement the Task Force provisioning API (temporary shared Linux groups).  
* \[ \] Implement the skills/propose and approval workflow endpoints.  
* \[ \] Build the Quarantine Sandbox for testing proposed Python code (IQ/OQ/PQ).  
* *Definition of Done:* A Worker proposes a new Python script tool. It passes QA in the sandbox, the Manager approves it, and the Kernel registers it as an executable endpoint for the team.

## **10\. Future Considerations & Scaling**

* **Multi-Node Clusters:** As the swarm grows beyond 50-100 agents, I/O or CPU may bottleneck. The Kernel should be designed to support Kubernetes (K3s), allowing Nullclaw agents to be distributed across a cluster of Linux VMs while the Kernel maintains the central DB.  
* **Memory Vector Databases:** Integrating a local vector database (like ChromaDB) managed by the Kernel. Agents could query a "Company Memory" endpoint to find past solutions or historical code snippets, rather than solely relying on their local text-based memory files.

## **11\. Development Roadmap (MVP Phasing)**

### **Phase 1: OS, DB, & Workspace Provisioning**

* \[ \] Initialize SQLite schema (nodes, budgets, forms\_ledger, master\_skills).  
* \[ \] Write Linux user creation scripts setting strict group permissions (Managers get rwx on subordinate folders).  
* \[ \] Scaffold the directory structure (inboxes, outboxes, drafts, skills).

### **Phase 2: Form State Daemon & Budgets**

* \[ \] Implement YAML parser daemon to move files and update forms\_ledger.  
* \[ \] Setup LiteLLM proxy and the Waterfall Budget logic in the DB.

### **Phase 3: Context Injector & Nullclaw Integration**

* \[ \] Write the templating engine to inject DB variables into AGENTS.md.  
* \[ \] Install Nullclaw, configuring its heartbeat to read /inbox/new/.

### **Phase 4: Corporate Workflows (The Skills)**

* \[ \] Author the Master SOPs (Markdown files explaining to agents *how* to fill out YAML forms).  
* \[ \] Test the full lifecycle: Worker runs out of money → fills Budget Request Form → puts in outbox → Daemon routes to Manager → Manager approves → Daemon updates DB → Budget increases.
