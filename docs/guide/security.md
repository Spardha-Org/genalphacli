# Security

GenAlpha CLI has three security surfaces: the parser (reading repos), the generator (producing code), and the generated MCP server (running as a process).

## Parser Security

The parser performs static analysis only — it never executes code from cloned repositories.

- **Git hooks disabled**: Clones with `--no-checkout`, sanitizes `.gitattributes` filter drivers (removes `filter=` directives), then checks out
- **`core.fsmonitor=false`**: Disables filesystem monitor hook
- **No submodule recursion**: `--no-recurse-submodules` prevents submodule-based attacks
- **No code execution**: Uses `ast.parse()` only — never `import`, `eval`, or `exec` on repo code
- **Repo size cap**: Rejects repositories larger than 500MB (checked via GitHub API before cloning)
- **Remote `$ref` blocked**: OpenAPI parser uses `RESOLVE_INTERNAL` only — remote URLs cannot be fetched
- **URL validation**: `urlparse()` rejects ports, userinfo, non-ASCII characters, fragments
- **Temp file isolation**: Clone directories under `~/.cache/genalphacli/` with `0700` permissions + `atexit` cleanup
- **`GIT_TERMINAL_PROMPT=0`**: Prevents credential prompts from hanging

## Generator Security

The generator produces Python code from graph.json data via Jinja2 templates.

- **Jinja2 SandboxedEnvironment**: Prevents template injection from malicious graph.json field values
- **String sanitization**: All graph values escaped before template rendering — triple-quotes, backslashes, Jinja2 delimiters (`{{ }}`, `{% %}`), and newlines
- **AST safety walk**: Post-generation scan walks the AST and rejects `eval`, `exec`, `os.system`, `subprocess.run`, `subprocess.Popen`, `__import__` calls
- **`cli_name` validation**: Must match `^[a-z][a-z0-9_]*$` — prevents path traversal and invalid Python identifiers
- **`base_url` validation**: Rejects private/loopback IPs (`127.x`, `10.x`, `172.16-31.x`, `192.168.x`) and `file://` scheme
- **Token CRLF prevention**: Generated clients reject auth tokens containing `\r`, `\n`, or `\0` bytes

## MCP Server Security

Generated MCP servers run as persistent processes communicating via JSON-RPC.

- **`ToolError` wrapping**: Raw exceptions never reach the AI — only intentional `ToolError` messages are returned as tool results. Stack traces, internal paths, and error details are masked.
- **No `print()` in generated server**: `print()` in stdio mode corrupts the JSON-RPC stream. Generated servers use `logging` (stderr) only.
- **Response truncation**: API responses are capped to prevent context window flooding attacks where massive responses push the system prompt out of the LLM's context.
- **Token isolation**: Auth tokens are never included in tool return values — they flow into the LLM context where they could be exfiltrated via prompt injection.
- **CRLF injection prevention**: Same token validation as CLI — rejects tokens with control characters.
- **Env var auth**: Tokens are read from environment variables at runtime, never hardcoded in generated code or config files.
