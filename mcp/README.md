# MCP Tool Layer

MCP is the tool boundary between agents and external capabilities.

Initial tool domains:

- GitHub — repositories, branches, code search, pull requests
- Filesystem — controlled workspace access
- Terminal — sandboxed tests and static analysis
- Database — schema inspection and read-only diagnostics
- Web — documentation and technical research

Mutating tools should be classified by risk and routed through the approval policy before execution.
