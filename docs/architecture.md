# Architecture Notes

## Execution model

A task enters through the API and becomes a stateful LangGraph execution. The planner creates a bounded plan. Specialist agents operate on shared state and call tools through MCP. Tool policy determines whether an action is read-only, requires approval, or is blocked.

## Safety boundary

The default posture is read-first and least privilege. Repository inspection, documentation retrieval, and test execution can be automated. Changes that create external side effects—such as pushing code, opening a pull request, modifying production data, deleting resources, or sending external messages—require explicit human approval.

## Evidence model

Important conclusions should retain evidence references: repository path, line/range when available, command output, retrieved document, or tool result. The final report should distinguish observed facts from agent hypotheses.
