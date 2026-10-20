# V0.1 architecture

Provider implementations own vendor transport. Agent identity and role are independent of provider identity; multiple agents can share one provider. A Team names its agent members and a Project references its Team. Tasks belong to projects and optionally reference a parent task.

TeamKernel is deterministic: registry, state transitions, persisted turn reservations, delegation, messages, revision counters and escalation. It imports only the provider contract. ThreeAgentWorkflow selects the fixed architect/engineer/reviewer sequence; provider selection lives in the CLI composition root.

SQLite stores projects, teams, providers, agents, sessions, tasks, messages, events, artifacts and decisions as validated JSON records with project indexes. Blackboard snapshots include goal, known facts, open questions, risks, decisions, tasks and artifacts. Session IDs are persisted, never credentials. Every message and task transition emits an event. Provider errors record error classes, not raw vendor diagnostics.

Hard ceilings: 12 provider calls per project, 2 revisions per original task, delegation depth 3 (root depth 0). Attempted turns reserve budget before calling a provider; counters survive kernel reconstruction. Revisions attach to the original task to avoid resetting counters. Invalid transitions fail. Exceeding a ceiling escalates the affected task without another model call. Each provider turn is bounded by time. These ceilings count runtime calls, not a vendor's internal tool/model iterations or tokens.

PoC limitations: single process and sequential workflow; collection writes/events are separate commits (not crash-atomic); no automatic workflow recovery; Codex thread resume is an adapter API only. Multi-process scheduling and crash recovery require transactions/leases and migration design before production. Provider protocol data is trusted local application data; this is not an untrusted-code sandbox. Demo tests execute Python in the isolated demo directory using the host interpreter.

Mock engineer copies original fixture code. Mock reviewer checks for a missing USAGE.md and requests one revision. Actual unittest execution occurs after implementation and revision, including a runtime-owned contract suite. This verifies scheduling and artifacts, not AI reasoning quality. Real mode never silently falls back after a model turn starts.
