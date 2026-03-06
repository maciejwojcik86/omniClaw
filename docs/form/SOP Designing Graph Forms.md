## **id: SKILL-ARCH-001 title: Designing and Managing Graph Forms (Workflow Engine) version: 1.0 effective_date: 2026-03-04 owner_department: platform_architecture risk_tier: high scope: [form_schemas, workflows, routing, stage_skills]**

# **Skill Purpose**

This document instructs you on how to create and deploy new, flexible business processes within the OmniClaw company. Communication between agents is not a simple "chat" – it relies on **Stateful Forms** managed by the Kernel's graph engine.

As an architectural agent or manager, your task is to map company processes into **Graph Schemas**, and then create dedicated instructions (Skills) for each step (Stage) in that graph.

## **1. Form Graph Architecture (Graph Engine)**
The Kernel uses JSON schemas to decide where to send the .md file from agent /outbox/pending/ folder. The agent prepares the md form file with YAML frontmatter, filling it out with metadata, target recipient, and the `decision` field. 

### **1.1 Markdown Form File with YAML frontmatter 

Each form is a markdown file is adnotated with following YAML header metadata. The file is with one agent at any given stage, and its stage and livecycle is tracked by kernel based on yaml metadata. This data is validated and linked via kernel with database. The md form document may grow as its content may be appended with various stakeholders agents as the form flows:

**form_type**: type name of approved form.
**description**: description and purpose of the form, outline of the workflow and who is involved in the cycle.
**stage**: current stage of the form, matching stages defined in the form workflow.json, stage is automatically managed by kernel during decision processing.
**decision**: agent writes here its action/decision, which are available as in the form workflow. The skill required for this stage must explain what decisions are available at this stage and based on what make them, these skills linked with form stages are giving agent guidance and instructions how to follow up with the skill. 
**target**: agent fills this out with name of target agent node (or human). kernel validated is target is valid agaisnt the json workflow. if target is restrictive (e.g. only one agent can do the review), this should be clearly stated in associated stage skill.


### **1.2 Form Nodes Structure `workflow.json`**

The workflows of the form lifecycle, stages as nodes, actions- decisions like approval, sent, etc. as edges.

Each form graph must have following data:
**form_type**: name of the form
**description**: brief but informative descritpion of the flow purpose, cycle etc.
**stages**: list of stages
Each stage of the form is defined as follows:

* **target**: Determines to whom the Kernel will send the form.
  * *Specific Agent*: E.g., "Agent_HR_01"
  * *Dynamic variable*: E.g., "{{initiator}}" (form creator), "{{any}}" can be send to any agent, routed based on value 'target' from YAML entered by the agent.
* **required_skill**: The name of the Skill (SOP) that the Kernel will automatically copy to the target agent's /skills/ folder. This Skill tells the agent what to do with the received form. No enforcement of skill needed for {{initiator}} as the form is already initiated from the skill agent have (e..g it must have skill "draft-internal-message" to write the draft and make it ready to send). In case of {{any}} the required skill should be distributed to all active agents.
* **decisions**: A dictionary mapping the agent's decision to the ID of the next stage. Decisions (action that agents can take) should be clearly described in required skill and if they result with some actions there shold be scirpts ready together with skill.

The final node should also be targeted to the agent, if for example form is reaching successful approval and new agent docs are aready and form is signed off for deployment, the last step may go to agent responsible for new deployment and run all actions in associated skill SOP

## **2. Creating a New Process (Your Tasks)**

When designing a new process (e.g., "Leave Request", "Agent Deployment", "Code Audit"), you **MUST** generate 3 elements:

1. **JSON Graph Schema**: Defining all stages, loops, and branches.
2. **MD Form Template**: An empty Markdown file with the appropriate YAML header and sections to be filled out, which agents will copy.
3. **Stage Skills**: You cannot create a single Skill for the entire process. You must create a separate .md file for each stage (e.g., one Skill for the Requesting Agent, another Skill for the Approving Manager).
   * *What must a Stage Skill contain?* Specific decision instructions (e.g., "Approve only if budget > 0"), references to available tools/scripts (e.g., check_budget.py), and precise information on which `decision` values the agent should enter in YAML to push the form forward or send it back.

## **3. Example Graph Configurations**

Below are three fundamental examples that you should use as models for your future projects.

### **Example 1: Simple Message**

The simplest point-to-point flow. Any agent can send a message to any other agent.

{
  "form_type": "internal_message",
  "description": "Standard point-to-point communication between agents.",
  "stages": {
    "DRAFT": {
      "target": "{{initiator}}",
      "required_skill": "draft-internal-message",
      "decisions": {
        "send": "RECEIVED"
      }
    },
    "RECEIVED": {
      "target": "{{any}}",
      "required_skill": "read-and-acknowledge-internal-message",
      "is_terminal": true
    }
  }
}

In this case flow doesnt need to archive the message. We could either add decision "acknowledge": "ARCHIVED" that would send to agent to archive the message but `read-and-acknowledge-internal-message` could simpler instruct receiving agent to run tool to archive the message itself. The first approach with delegated agent may be better in case of more complicated deplyoment where at closure not only one action is required, but also some creative work like writing implenetation report, or review it feature is running etc.

* **Related Skills:**
  * draft-internal-message: Skill Teaches the agent how to fill out the YAML (target_node_id, subject) and save it in the outbox with the send action.
  * skill_read_and_acknowledge: Teaches the target agent to analyze the content upon waking up, add a task to TODO.md, and change the action to acknowledge (so the Kernel closes the process) or reply (to reverse the direction).

### **Example 2: GMP Deviation Reporting**

A complex quality process. Contains loops (returning for correction) and dynamic target mapping (supervisor).

{  
  "form_type": "gmp_deviation",  
  "description": "Process for reporting errors, assessing impact, and implementing CAPA according to GMP.",  
  "stages": {  
    "1_INITIAL_REPORT": {  
      "target": "{{initiator}}",  
      "required_skill": "gmp_deviation_reporting",  
      "decisions": {  
        "submit_for_assessment": "2_IMPACT_ASSESSMENT"  
      }  
    },  
    "2_IMPACT_ASSESSMENT": {  
      "target": "Agent_QA_Triage_01",   
      "required_skill": "gmp_impact_assessment",  
      "decisions": {  
        "requires_investigation": "3_INVESTIGATION",  
        "close_no_impact": "5_CLOSED",  
        "return_for_clarification": "1_INITIAL_REPORT"  
      }  
    },  
    "3_INVESTIGATION": {  
      "target": "CMC_Investigator_Agent",   
      "required_skill": "gmp_root_cause_capa",  
      "decisions": {  
        "submit_capa_plan": "4_QA_APPROVAL"  
      }  
    },  
    "4_QA_APPROVAL": {  
      "target": "Agent_QA_Manager_01",  
      "required_skill": "gmp_capa_approval",  
      "decisions": {  
        "approve_capa": "5_CLOSED",  
        "reject_capa": "3_INVESTIGATION"  
      }  
    },  
    "5_CLOSED": {  
      "target": "GMP_Archiver_agent",  
      "required_skill": "gmp_deviation_archiving",  
      "is_terminal": true  
    }  
  }  
}

**Stage Skill Architecture for GMP:**
In stage 2_IMPACT_ASSESSMENT, gmp_impact_assessment instructs the QA agent to append a new section to the Markdown form: ## Impact Assessment. The agent also has access to a log verification tool. If the report is unclear, the agent enters `decision: return_for_clarification` in YAML, which the Kernel automatically routes back to the creator.


### **Example 3: Deploy New Claw Agent**

A multi-departmental process requiring financial and HR authorization, and final approval from the Director, before the Kernel physically creates a Linux user.

{
  "form_type": "deploy_new_agent",
  "description": "Cross-departmental process for creating a new AI employee.",
  "stages": {
    "1_BUSINESS_CASE": {
      "target": "{{initiator}}",
      "required_skill": "draft-agent-business-case",
      "decisions": {
        "submit_to_hr": "2_HR_REVIEW"
      }
    },
    "2_HR_REVIEW": {
      "target": "Department_Head_HR",
      "required_skill": "review-agent-role-and-template",
      "decisions": {
        "approve_to_finance": "3_FINANCE_REVIEW",
        "return_to_initiator": "1_BUSINESS_CASE"
      }
    },
    "3_FINANCE_REVIEW": {
      "target": "Department_Head_Finance",
      "required_skill": "allocate-agent-budget",
      "decisions": {
        "approve_to_director": "4_DIRECTOR_APPROVAL",
        "return_to_hr": "2_HR_REVIEW"
      }
    },
    "4_DIRECTOR_APPROVAL": {
      "target": "Agent_000_Director",
      "required_skill": "final-agent-signoff",
      "decisions": {
        "execute_deployment": "5_AGENT_DEPLOYMENT",
        "return_to_finance": "3_FINANCE_REVIEW",
        "reject": "6_ARCHIVED"
      }
    },
    "5_AGENT_DEPLOYMENT": {
      "target": "HR_Agent_Spawner",
      "required_skill" : "deploy-new-claw-agent",
      "decisions": {  
        "deploy_and_archive": "6_ARCHIVED"  
      }  
    },  
    "6_ARCHIVED": {  
      "target": "HR_Archiver",  
      "required_skill" : "archive-agent-deployment-form",
      "is_terminal": true  
    }  
  }  
}

This form allows to make multiple decisions at any stage, return them back for review with some feedback, and at the end landing with archiver to close the flow in two ways, either request rejected or successfully deployed. archive-agent-deployment-form skill may instruct agent to do several actions at the end depending on the previous decision in yaml metadata from previous agent.
