# Change Proposal: strengthen-agent-harness

## Summary
Upgrade the agent harness from "works" to "governable and observable" by adding explicit event contracts, tool policy enforcement, context assembly, replay/eval, session memory separation, and HTTP schema contracts.

## Motivation
Current behavior is centered around the ReAct loop and loosely structured dictionaries. This limits reliability for long-term evolution, traceability, and security controls.

## Goals
1. Introduce typed observation events across engine/tool/task flows.
2. Enforce policy checks before tool execution.
3. Centralize context assembly in application layer.
4. Add replay + evaluation capability from packet logs.
5. Separate task bookkeeping from session memory.
6. Define HTTP request/response schemas.

## Non-Goals
1. Replacing current model provider.
2. Converting into distributed/microservice architecture.
3. Large frontend redesign.

## Scope
- Backend architecture and contracts only.
- Keep CLI and FastAPI behavior consistent for core user flows.

## Risks
1. Event schema migration may impact historical log readers.
2. Policy defaults may reduce completion rate if too strict.
3. Additional context assembly may increase token cost.

## Rollout Plan
1. Dual-write old/new event format for one release window.
2. Enable policy in audit mode, then enforce mode.
3. Promote replay metrics into CI checks.
