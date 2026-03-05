the root/workspace folder will contain all soft, configuration artifacts of related to the company 'culture'
it should have folder with master skills, which approved copies will be deployed to agents. and it will also contain folder with approved form workflows.

check folder `templates`, i believe that it contians some old ideas for templating, probably you can delete it.

review `src/omniclaw/forms` implementation.
The forms should be defined in json file in the way as provided in example below, this is an example of skill instructions for authoring new forms:

`docs/form/SOP Designing Graph Forms.md`

ensure that forms omniclaw implementation follow author intent as described above.

the forms-ledger-state-machine should focus on moving the forms between agents and keeping track of its stage, as well as validating the forms to ensure that they are distributed along the nodes. the kernel should also ensure that required skills are available and are distributed to participant agents.

sending message is just one trival example to communicating between agents, so please make it more general. To keep it simple all actions in system will be triggered by agents as instructed in form stage specific skills.
The end node may just target archiver LLM agent with skill instructing it to summarize form implementation and archive it, by running some tools scripts refered in skill. 

At the end of this iteration I want from you to consider this Milestone finished following:

- IPC updated in the way to handle and route generic forms according to graph, instead of simple message. system changes the stage as it follows the decision and edge of graph, copy files between users, changes its stage (if possible edit also frontmatter stage) as per decision, update database, and copy the backup of forms message in `workspace/form_archive` folder of this repo (save them in some subfolder structure that would make sense to find them later). 
IPC should understand and allow to use as target: agent node id in case if we want to delegate it to specific target and some variables in {{}}, we will start with just few like initiator - just to keep track who started, and later nodes may return the form to {{initiator}}, {{any}} - indicating that the target can be any agent.

- system allowing add new form type based on the json graph definition and other form metadata, adding it to the database and keeping the json copy in `workspace/forms/<form_name>/workflow.json`

- skills required for all stages of form lifecycle, their master copies should be stored in 
`workspace/forms/<form_name>/skills/<skill_name>/SKILL.md` + other linked with skill templates, docs, tools and scripts. 
at authoring of new skill or updating its version to new revision, kernel must validate if master skills exisits and matches the names as defined in workflow.json

- create a main skill for agents creating and authoring new forms and workflows. This skill should be similiar in scope and details to `SOP Designing Graph Forms.md` but including specific instructions and refer to tools allowing to author and add to database (call endpointts or cli scripts) new form, with associated skills and json workflow files. Completly new agent after reading this skill should be able to understand how to build forms, how they work (as they are md files with yaml frontmatter, that agents can edit (e.g. in frontmatter write to whom send message) and that kernel manage sending them to next nodes, if dropped in outbox folder etc.), it should also have tools to edit and update and delete forms. Agents wont have access to wroskapce forms mastercopies, they will need to be added there using kernel endpoitns (to update database, distribute skills to relevant agents, keep version control etc).

- then using this new skill I would like you to create two forms from example in `SOP Designing Graph Forms.md`, message and new agent deployment (ignore gmp deviation). Not only creating a workflow.json in workspace as instructed, but also creating all required skills (in form subfolder)
