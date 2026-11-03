# Threat model

The adversary may modify retrieved document text, API bodies or metadata. Trusted components are the user objective, system instructions, scenario evaluator ground truth and local runtime code. A contradiction may be a benign data-quality issue rather than an attack.

Targeted failures: disclosure of synthetic canaries, unauthorized simulated email/record changes, acceptance of manipulated statuses, and unwarranted confidence under conflicting evidence. Six local tools provide read fixtures and record sensitive operations in memory. They have no network or external mutation capability. There is no shell execution or dynamic evaluation of fixture content.

Baseline instructions are not a security boundary. Its mandatory input interface validation cannot establish authorization. Later safeguards must use trusted authorization independently of tool content; independent review remains fallible. The current fake provider cannot be attacked because it does not interpret messages.

Out of scope: real credentials, real users, malware execution, OS sandbox escape, external MCP servers, real financial or communication actions, model-training attacks and claims about deployed systems. The tool abstraction is compatible in shape with named JSON-schema tools, but is not an MCP transport implementation.
