# V0.3.0 conversational workspace

The default page is **与 AI 团队协作**. It uses the existing TaskManager,
TeamKernel, EventBus and Blackboard collections; it is not a simulated chat.
Opening, refreshing and reading history never calls a model.

## Start without model calls

From the checkout root, with the project's Python environment activated:

```powershell
python -m pip install -e ".[test]"
npm.cmd --prefix console ci --ignore-scripts
npm.cmd --prefix console run build
python scripts/team_console.py --port 8765
```

Open `http://127.0.0.1:8765`. Create a conversation and add requirements. These
operations only persist local records. Historic dashboards remain available.
No credentials should be entered in conversation text.

## Explicit real execution (not run during V0.3.0 development)

The source runtime needs the pinned optional SDK and an authenticated Codex CLI:

```powershell
python -m pip install -e ".[dsh]"
# Set this to YOUR existing DSH home, not to an API key:
$env:AI_TEAM_DSH_HOME = "<absolute-existing-DSH-home>"
python scripts/team_console.py --port 8765 --enable-models
```

Use an available port and stop an earlier console instance first. Do not launch
two runtime instances against the same collaboration database or DSH home.
Save work and exit the DSH desktop, its background Host and other CLI/SDK
processes sharing that home first. No logout, new API key, credential copying or
system environment changes are needed. DSH owns its account authorization.

The route is `deepseek-account`, model `deepseek-flash`, profile `sdk`,
`max_tokens=4096`, `reasoning_effort=off`. These reuse the previously verified
adapter settings. See [DSH integration notes](dsh-desktop-reuse.md).
The [official SDK reference](https://github.com/deepseek-ai/deepseek-harness/blob/master/python/sdk/README.md)
documents explicit homes, route selection and output/reasoning parameters.
This release does not alter the client installation or SDK profile settings.

The DSH SDK profile retains its own tool permissions. A no-tools instruction
is an advisory prompt, not an OS sandbox. Use trusted requests only. Codex
discussion uses the app-server `read-only` thread and `readOnly` turn policy;
implementation uses its existing workspace-write policy with network disabled.
Approval policy is `never`: unsupported actions must fail, not prompt for
unattended elevation. The workspace boundary does not claim to deny all reads
outside the directory. Do not treat either provider as an untrusted-code sandbox.

1. Create a goal, add constraints and acceptance criteria.
2. Check the planning consent box and start discussion: DSH proposes, Codex
   critiques the persisted proposal, DSH reads the critique and produces a plan.
   An ASK response pauses for user clarification in the same conversation.
3. Review the plan, optionally edit its JSON or supplement requirements.
   Supplementing invalidates the old plan. A second discussion is explicit;
   no more than two discussion cycles are allowed.
4. Confirm the exact plan version and code-execution consent. Codex receives
   the persisted plan, implements 1–4 dependency-ordered steps, runs tests, and
   writes `test-results.txt`. DSH then reviews actual files and transport evidence.
5. Inspect the final decision, task states, messages and artifact hashes.

No automatic retry or rework is performed. On REQUEST_CHANGES, inspect the
findings and make a new explicitly approved conversation. Cancel is best effort:
Codex supports interrupt; DSH closes its owned runtime. Cancellation never rolls
back files. Process interruption is shown explicitly and cannot silently replay
a paid turn; cancel the interrupted conversation before starting another.

## Persistence and protocol

New records use `runs/conversations/blackboard.sqlite`; code artifacts use
`runs/conversations/workspace/<conversation-id>`. Existing runs are untouched.
There is no schema migration: conversation state and plans are decisions, user
and agent messages use messages, and lifecycle transitions use events. A root
CONVERSATION task links user input. `conversation_id` equals `project_id`.

Existing message semantics are reused: PROPOSE=plan/proposal/revision,
ASK=question, CHALLENGE=critique, ASSIGN=assignment,
COMPLETE=implementation output, APPROVE/REQUEST_CHANGES=review. Metadata adds
conversation ID, discussion round, artifact references and recorded execution
status. Existing IDs, sender/recipient, timestamp and task IDs are retained.
INPUT_REFERENCES and CROSS_REVIEW events link consumed messages, plans and files.
No duplicate message tables or migration of historic schemas is introduced.

Plans contain `steps` with unique `id`, `agent: "Codex"`, `instruction` and
`depends_on` referencing earlier steps. One conversation runs at a time per
server; tasks are serial. Real parallel execution is **NOT_SUPPORTED** because
the adapters share sessions/process state and the implementation workspace.
Pause/resume of an active model turn is **NOT_SUPPORTED**. Cancel is available.

Tests use Mock providers exclusively. A successful offline cycle does not
establish DSH/Codex availability or a successful real V0.3.0 workflow.
WorkBuddy remains PARTIAL / AUTH_REQUIRED and cannot join this workflow.

## Review evidence and limitations

Codex app-server `item/completed` commandExecution events supply command,
completion status, exit code and bounded output. At least one recognized test
command (pytest/unittest/npm test) must complete with exit code zero, and no
captured test command may fail. Otherwise execution stops before DSH review.
These events are kept separately from the model-authored test-results.txt.
The host does not independently rerun tests or prove test-suite adequacy.

Review includes bounded text sources, exact SHA-256 hashes, original goal,
approved plan and captured command evidence. Links, junctions, hidden folders
and non-allowlisted files are excluded. Unsafe, missing or oversized evidence
fails closed; content is not silently truncated into an approval. Files must
still match the reviewed hashes after the review. JSON review conclusions are
strictly APPROVE or REQUEST_CHANGES with at most three findings.

Limits: 3 tasks per discussion cycle, up to 4 implementation tasks plus 1
review; at most 11 application tasks across two cycles. SDK/internal HTTP
retries are unknown. The underlying kernel has an additional 12-turn ceiling.
Test commands and source evidence are currently optimized for small coding
tasks, not arbitrary research/data pipelines. Agent Management's live online
status remains UNKNOWN; recorded RUNNING tasks are not proof of connectivity.

## Windows package

The CI installer includes the collaboration UI and offline backend. CI does
not install the optional DSH SDK/runtime or private authorization. Therefore
the packaged build does not claim out-of-box real DSH execution. Use the
source entry above for the first explicitly authorized real workflow.
`AI_TEAM_ENABLE_MODELS=1` enables desktop endpoints only; it does not install
dependencies or establish authorization. Default desktop startup remains safe.
