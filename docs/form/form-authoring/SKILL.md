---
name: form-authoring
description: Designing and Managing new company formal graph based Form workflow.
license: MIT
metadata:
  author: omniclaw
  version: "0.1"
---

# **Skill Purpose**

This document instructs you on how to create and deploy new, flexible business processes within the OmniClaw company. Communication between agents is not a simple "chat" – it relies on **Stateful Forms** managed by the Kernel's graph engine.

As an architectural agent or manager, your task is to map company processes into **Graph Schemas**, and then create dedicated instructions (Skills) for each step (Stage) in that graph.

## **1\. Form Graph Architecture (Graph Engine)**

The Kernel uses JSON schemas to decide where to send the .md file from your /outbox/pending/ folder. The decision from one state to another occurs when you change the action\_taken value in the form's YAML header.

### **1.1 Node Structure (Stage)**

Each stage of the form is defined as follows:

* **target**: Determines to whom the Kernel will send the form.  
  * *Specific Agent*: E.g., "Agent\_HR\_01"  
  * *Dynamic variable*: E.g., "{{initiator}}" (form creator), "{{initiator\_manager}}" (creator's supervisor), "{{frontmatter.target\_node\_id}}" (value entered directly into the YAML by the agent).  
  * *System*: E.g., "kernel\_archive" or "kernel\_provisioning" (terminal stage, triggers hardcoded Kernel logic).  
* **required\_skill**: The ID of the Skill (SOP) that the Kernel will automatically copy to the target agent's /skills/ folder. This Skill tells the agent what to do with the received form.  
* **decisions**: A dictionary mapping the agent's decision (saved in YAML as action\_taken) to the ID of the next stage.

## **2\. Creating a New Process (Your Tasks)**

When designing a new process (e.g., "Leave Request", "Agent Deployment", "Code Audit"), you **MUST** generate 3 elements:

1. **JSON Graph Schema**: Defining all stages, loops, and branches.  
2. **MD Form Template**: An empty Markdown file with the appropriate YAML header and sections to be filled out, which agents will copy.  
3. **Stage Skills**: You cannot create a single Skill for the entire process. You must create a separate .md file for each stage (e.g., one Skill for the Requesting Agent, another Skill for the Approving Manager).  
   * *What must a Stage Skill contain?* Specific decision instructions (e.g., "Approve only if budget \> 0"), references to available tools/scripts (e.g., check\_budget.py), and precise information on which action\_taken options the agent should enter in the YAML to push the form forward or send it back.

## **3\. Example Graph Configurations**

Below are three fundamental examples that you should use as models for your future projects.

### **Example 1: Simple Message**

The simplest point-to-point flow. Any agent can send a message to any other agent.

{  
  "form\_type": "internal\_message",  
  "description": "Standard point-to-point communication between agents.",  
  "stages": {  
    "DRAFT": {  
      "target": "{{initiator}}",  
      "required\_skill": "skill\_draft\_formal\_message",  
      "decisions": {  
        "send": "RECEIVED"  
      }  
    },  
    "RECEIVED": {  
      "target": "{{frontmatter.target\_node\_id}}",  
      "required\_skill": "skill\_read\_and\_acknowledge",  
      "decisions": {  
        "acknowledge": "ARCHIVED",  
        "reply": "RECEIVED"   
      }  
    },  
    "ARCHIVED": {  
      "target": "kernel\_system",  
      "is\_terminal": true  
    }  
  }  
}

* **Related Skills:**  
  * skill\_draft\_formal\_message: Teaches the agent how to fill out the YAML (target\_node\_id, subject) and save it in the outbox with the send action.  
  * skill\_read\_and\_acknowledge: Teaches the target agent to analyze the content upon waking up, add a task to TODO.md, and change the action to acknowledge (so the Kernel closes the process) or reply (to reverse the direction).

### **Example 2: GMP Deviation Reporting**

A complex quality process. Contains loops (returning for correction) and dynamic target mapping (supervisor).

{  
  "form\_type": "gmp\_deviation",  
  "description": "Process for reporting errors, assessing impact, and implementing CAPA according to GMP.",  
  "stages": {  
    "1\_INITIAL\_REPORT": {  
      "target": "{{initiator}}",  
      "required\_skill": "skill\_gmp\_deviation\_reporting",  
      "decisions": {  
        "submit\_for\_assessment": "2\_IMPACT\_ASSESSMENT"  
      }  
    },  
    "2\_IMPACT\_ASSESSMENT": {  
      "target": "Agent\_QA\_Triage\_01",   
      "required\_skill": "skill\_gmp\_impact\_assessment",  
      "decisions": {  
        "requires\_investigation": "3\_INVESTIGATION",  
        "close\_no\_impact": "5\_CLOSED",  
        "return\_for\_clarification": "1\_INITIAL\_REPORT"  
      }  
    },  
    "3\_INVESTIGATION": {  
      "target": "{{initiator\_manager}}",   
      "required\_skill": "skill\_gmp\_root\_cause\_capa",  
      "decisions": {  
        "submit\_capa\_plan": "4\_QA\_APPROVAL"  
      }  
    },  
    "4\_QA\_APPROVAL": {  
      "target": "Agent\_QA\_Manager\_01",  
      "required\_skill": "skill\_gmp\_capa\_approval",  
      "decisions": {  
        "approve\_capa": "5\_CLOSED",  
        "reject\_capa": "3\_INVESTIGATION"  
      }  
    },  
    "5\_CLOSED": {  
      "target": "kernel\_archive",  
      "is\_terminal": true  
    }  
  }  
}

* **Stage Skill Architecture for GMP:** \* In stage 2\_IMPACT\_ASSESSMENT, skill\_gmp\_impact\_assessment instructs the QA agent to append a new section to the Markdown form: \#\# Impact Assessment. The agent also has access to a log verification tool. If the report is unclear, the agent enters action\_taken: return\_for\_clarification in the YAML, which the Kernel automatically routes back to the creator.  
  * In stage 3\_INVESTIGATION, the Kernel dynamically resolves the {{initiator\_manager}} variable, sending the form to the supervisor of the agent who made the error, forcing them to write a CAPA plan.

### **Example 3: Deploy New Claw Agent**

A multi-departmental process requiring financial and HR authorization, and final approval from the Director, before the Kernel physically creates a Linux user.

{  
  "form\_type": "deploy\_new\_agent",  
  "description": "Cross-departmental process for creating a new AI employee.",  
  "stages": {  
    "1\_BUSINESS\_CASE": {  
      "target": "{{initiator}}",  
      "required\_skill": "skill\_draft\_agent\_business\_case",  
      "decisions": {  
        "submit\_to\_hr": "2\_HR\_REVIEW"  
      }  
    },  
    "2\_HR\_REVIEW": {  
      "target": "Department\_Head\_HR",  
      "required\_skill": "skill\_review\_agent\_role\_and\_template",  
      "decisions": {  
        "approve\_to\_finance": "3\_FINANCE\_REVIEW",  
        "reject\_to\_initiator": "1\_BUSINESS\_CASE"  
      }  
    },  
    "3\_FINANCE\_REVIEW": {  
      "target": "Department\_Head\_Finance",  
      "required\_skill": "skill\_allocate\_agent\_budget",  
      "decisions": {  
        "approve\_to\_director": "4\_DIRECTOR\_APPROVAL",  
        "reject\_to\_hr": "2\_HR\_REVIEW"  
      }  
    },  
    "4\_DIRECTOR\_APPROVAL": {  
      "target": "Agent\_000\_Director",  
      "required\_skill": "skill\_final\_agent\_signoff",  
      "decisions": {  
        "execute\_deployment": "5\_KERNEL\_PROVISIONING",  
        "reject\_kill": "6\_ARCHIVED\_REJECTED"  
      }  
    },  
    "5\_KERNEL\_PROVISIONING": {  
      "target": "kernel\_provisioning\_daemon",  
      "is\_terminal": true  
    },  
    "6\_ARCHIVED\_REJECTED": {  
      "target": "kernel\_archive",  
      "is\_terminal": true  
    }  
  }  
}

* **Tools and Skills for Deployment:**  
  * skill\_review\_agent\_role\_and\_template (For HR): Instructs the HR agent to verify whether the form attachment contains a correctly formatted persona\_template.md file. The HR agent uses a tool that verifies the {{placeholders}} variables. If mandatory policies are missing, it rejects the request.  
  * skill\_allocate\_agent\_budget (For Finance): This Skill provides the validate\_budget\_reserves.py script. The Finance Agent must run this script based on the form's YAML. If the requesting department has LiteLLM reserves, the agent appends the section \#\# Financial Decision: Approved $X/day and forwards the form to the Director.  
  * Reaching the 5\_KERNEL\_PROVISIONING stage is intercepted by hardcoded Kernel logic, which executes useradd scripts on the Linux system.