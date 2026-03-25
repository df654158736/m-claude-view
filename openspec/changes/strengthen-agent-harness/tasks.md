# Tasks: strengthen-agent-harness

## 1. Event Contract
- [ ] Add domain event models (`Event`, `EventType`, payload variants).
- [ ] Replace raw packet dict creation with event builder.
- [ ] Add serializer/deserializer and compatibility adapter.
- [ ] Update packet store readers to support new event schema.

## 2. Tool Policy
- [ ] Add policy module with allow/deny rules and reason codes.
- [ ] Add pre-execution policy check in engine tool phase.
- [ ] Emit policy decision events to packet log.
- [ ] Add tests for allow, deny, and malformed args.

## 3. Context Assembly
- [ ] Add `ContextProvider` interface and default providers.
- [ ] Add application-level context assembler before LLM request.
- [ ] Record context source metadata in observation events.
- [ ] Add tests for provider ordering and truncation behavior.

## 4. Replay and Evaluation
- [ ] Add replay use case from packet logs.
- [ ] Add metrics output (success rate, avg iterations, tool calls).
- [ ] Add CLI command for replay/eval mode.
- [ ] Add golden tests for deterministic replay parsing.

## 5. Session vs Task State
- [ ] Introduce session store abstraction.
- [ ] Move cross-run conversation memory into session store.
- [ ] Keep task state in task service only.
- [ ] Add tests for concurrent tasks across sessions.

## 6. HTTP Contract Schemas
- [ ] Add Pydantic request/response models.
- [ ] Replace ad-hoc dict responses with typed schemas.
- [ ] Add API validation tests for 200/4xx paths.
- [ ] Update frontend API expectations if field names change.
