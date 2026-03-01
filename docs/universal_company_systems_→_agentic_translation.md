# Principle
Start tiny, grow organically. The **Director** seeds only the minimum meta‑departments and hands them goals. Those heads then design specifics (onboarding, approvals, workflows) and hire/shape their teams over time. Authority and trust flow top‑down; initiative flows bottom‑up.

---

# What all companies share → How it maps to an agentic company

| Human‑Company System | Purpose (human world) | Agentic Translation (actors · artifacts · processes) | v0 Guidance |
|---|---|---|---|
| **Vision & Strategy** | Set direction, priorities, and risk appetite | Director agent owns **Company Constitution** + quarterly **Intent**; propagated to all agents as inherited prompt layer | Seed now: publish Constitution v0 + Intent v0 |
| **Governance** | Decide who can decide; prevent conflicts | Approval graph; CODEOWNERS‑style rules; separation of duties; audit logs | Seed now: minimal rules for structure/tool changes |
| **Org Design** | Roles, teams, reporting lines | **Org Graph** manifest: departments, heads, managers, workers | Seed now: 4 seeds (Platform, Governance, Finance, HR) |
| **Financials & Budgeting** | Allocate resources; ensure solvency | Budget tokens per dept/agent; daily reset; spend ledger; forecasts; rebalancing requests | Seed now: daily quotas + per‑task cap + ledger |
| **Planning (OKRs/Roadmap)** | Translate strategy to goals & work | Company → Dept → Agent OKR trees; weekly planning cadence; dependency mapping | Seed later: simple quarterly goals; weekly review loop |
| **People/HR** | Hire, onboard, develop, offboard | **HR Head** defines lifecycle states; skills matrix; promotion/demotion rules; performance reviews; probation | Seed now: create HR Head; task them to author v0 onboarding |
| **Legal/Compliance** | Reduce liability; meet regulations | Policy library in Constitution; compliance checks in approvals; incident reporting | Seed later: start with simple prohibited actions + data rules |
| **Security & Risk** | Protect assets; manage threats | Tool/data allowlists; secrets vault; risk register; red‑team evaluations | Seed now: least‑privilege tool scopes + secret policy |
| **IT/Platform** | Enable work; keep lights on | Platform Head owns repos, CI/CD, tool registry, runtime orchestrator, kill switches | Seed now: create Platform Head + tool registry |
| **Knowledge & Docs** | Keep shared memory | **Agent Files**, Dept Charters, SOPs; search index; decision log | Seed now: templates + mandatory Agent File |
| **Operations/Delivery** | Turn goals into outputs | Task tickets, queues, SLAs; hand‑offs; scheduler; backoff/retry | Seed later: minimal ticket schema + queue |
| **Quality & Improvement** | Ensure reliability; reduce defects | Test harnesses, evals, scorecards; postmortems; CAPA‑like loops | Seed later: smoke tests + incident template |
| **Procurement/Vendors** | Acquire tools/services | Tool request → review → contract/limits; vendor registry | Seed later: simple tool request workflow |
| **Customer/Stakeholders** | Understand and serve needs | Product/Service Heads; feedback loops; satisfaction metrics | Optional early: a small Product Head if delivering value externally |
| **Comms (internal/external)** | Align people; manage reputation | Change logs; release notes; incident comms; status pages | Seed later: lightweight change log |
| **Data & Analytics** | Measure reality; guide decisions | KPI catalog; dashboards; cost heatmaps; policy‑violation reports | Seed now: cost + approval latency + success rate |
| **Project/Portfolio** | Choose the right work | Intake RFCs; prioritization council (managers); capacity planning | Seed later: simple RFC form + weekly triage |
| **Change Management** | Ship safely and predictably | PR gates; feature flags; staged rollouts; freeze windows; rollbacks | Seed now: PR gates + basic canary/disable switch |
| **Incident Management** | Respond to failures | Kill switches; severity levels; on‑call manager; postmortems | Seed now: per‑agent/per‑dept/global kill switches |

---

# Core artifacts to standardize early
- **Company Constitution** (values, prohibitions, approval rules, escalation)
- **Org Graph** (departments, roles, reporting lines)
- **Agent Manifest** (mission, autonomy level, budget, tools, KPIs, scopes)
- **Dept Charter** (mandate, approvals, KPIs, budgets, incident thresholds)
- **Request Types** (Hire/Assign, Tool Access, Budget Rebalance, Cross‑Team Workflow)
- **Proposal Types** (Prompt change, Tool attach, Workflow edit, Spawn agent)
- **Budget Ledger** (append‑only, per agent/task/tool)
- **Change Log** (what changed, who approved, why)

---

# Seed now vs. let emerge
**Seed now (Director creates and delegates):** Constitution v0, Org Graph v0 (4 heads), Budget system (daily reset + caps + ledger), Agent Manifest template, Request/Proposal schemas, Kill switches, Cost/KPI basics.

**Let emerge (owned by department heads):** Onboarding specifics, performance review rubrics, detailed approval matrices, SOPs, test/eval suites, portfolio process, comms cadence, vendor policies.

---

# Early goals for the first heads
- **Platform:** stand up repos, manifests, tool registry, runtime toggles, CI checks, kill switches.
- **Governance:** finalize approval graph, policy checks, audit log format, incident severity scale.
- **Finance:** mint daily budgets, set rebalancing rules, publish cost dashboard, alert thresholds.
- **HR:** draft lifecycle states + onboarding playbook; define promotion/demotion criteria and review cadence.

---

# Interfaces (APIs) that everything plugs into
- **Requests:** Hire/Assign, Tool Access, Budget Rebalance, Cross‑Team Workflow
- **Proposals:** Prompt change, Tool attach, Workflow edit, Spawn agent
- **Reports:** KPI snapshots, cost summaries, incident reports
- **Decisions:** Approve / Deny / Ask‑changes with rationale

---

# Success criteria for v0
- One Director + 4 heads launched with budgets and charters
- HR delivers onboarding v0 for new agents within 1–2 iterations
- At least one safe cross‑dept request executed end‑to‑end
- All durable changes captured in change log with approvals and links to artifacts
- Costs contained by daily caps; kill switches verified in simulation

