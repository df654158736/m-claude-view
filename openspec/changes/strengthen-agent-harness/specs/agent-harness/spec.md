# Capability: agent-harness

## CHANGED Requirements

### Requirement: Agent execution must emit typed observation events
The harness MUST emit typed events for user input, llm request/response, tool execution, policy decision, and final outcome.

#### Scenario: tool call emits policy decision before execution
- **WHEN** the model requests a tool call
- **THEN** the harness emits a `policy_decision` event first
- **AND** tool execution occurs only if decision is `allow`
- **AND** denial includes a machine-readable reason code

### Requirement: Tool execution must be governed by explicit policy
Tool execution MUST be validated against configurable rules before runtime invocation.

#### Scenario: disallowed command is blocked
- **GIVEN** policy denies `bash` command pattern
- **WHEN** tool call arguments match the denied pattern
- **THEN** execution is blocked
- **AND** the model receives a structured denial message

### Requirement: Context assembly must be explicit and inspectable
The harness MUST assemble prompt context via provider interfaces and retain source metadata.

#### Scenario: multiple providers contribute context
- **WHEN** a task is processed
- **THEN** context includes ordered provider outputs
- **AND** each output records source identifier and token budget usage

### Requirement: Replay and evaluation must be supported
The system MUST provide offline replay from packet logs and report key performance metrics.

#### Scenario: replay report generation
- **WHEN** replay is run on a packet log file
- **THEN** report contains success rate, average iterations, and average tool calls

### Requirement: Session memory and task state must be separated
The harness MUST store conversation/session memory independently from async task lifecycle data.

#### Scenario: concurrent tasks in different sessions
- **WHEN** two sessions run tasks concurrently
- **THEN** task status isolation is preserved
- **AND** session memory does not leak between sessions

### Requirement: HTTP endpoints must use schema contracts
HTTP API MUST validate requests and return typed response bodies.

#### Scenario: invalid ask payload
- **WHEN** `/api/ask` receives missing or empty `question`
- **THEN** API returns validation error response
- **AND** no task is created
