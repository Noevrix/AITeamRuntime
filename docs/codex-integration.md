# Codex integration — 2026-10-19

Official CLI discovered on PATH: codex-cli 0.153.4. app-server help and JSON schema generation succeeded. Schema inspection confirmed thread/start, thread/resume, turn/start, turn/interrupt and completed-item/turn notification shapes. Generated schemas and environment paths are not checked into the repository.

[Official app-server documentation](https://learn.chatgpt.com/docs/app-server) is the transport reference. The adapter launches stdio, initializes, checks account/read, creates/resumes threads, sends turns and accepts only completed structured results. Interactive server requests fail closed; the demo uses workspace-write, network disabled and approvalPolicy never. No bypass flag is used. Persistent thread IDs are stored in SQLite. Streaming is not advertised because V0.1 consumes completed messages only.

Initial sandboxed probes: codex login status returned "Could not find home directory"; adapter handshake disconnected. This establishes CLI availability, not usable authentication or inference. No authentication files were opened. See the acceptance report for final probe results.

Missing CLI: follow [official CLI installation](https://developers.openai.com/codex/cli), then use official codex login and ai-team doctor from a normal terminal. Protocol tests use a fake RPC server; these do not verify real model access.

Final verification: normal-permission official login status reported Logged in using ChatGPT. An authorized run outside the restricted command sandbox successfully completed real Codex implementation and revision, with DSH/WorkBuddy mocked. Both host verification rounds passed 11 unittest cases. The earlier failure was execution-environment-specific. No authentication file was read by this project.
