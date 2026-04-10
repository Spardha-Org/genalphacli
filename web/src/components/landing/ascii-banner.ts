export const ASCII_ART = [
  " ██████╗ ███████╗███╗   ██╗ █████╗ ██╗     ██████╗ ██╗  ██╗ █████╗ ",
  "██╔════╝ ██╔════╝████╗  ██║██╔══██╗██║     ██╔══██╗██║  ██║██╔══██╗",
  "██║  ███╗█████╗  ██╔██╗ ██║███████║██║     ██████╔╝███████║███████║",
  "██║   ██║██╔══╝  ██║╚██╗██║██╔══██║██║     ██╔═══╝ ██╔══██║██╔══██║",
  "╚██████╔╝███████╗██║ ╚████║██║  ██║███████╗██║     ██║  ██║██║  ██║",
  " ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝",
];

export interface CommandResult {
  output: string;
  isAscii?: boolean;
}

export const COMMANDS: Record<string, () => CommandResult> = {
  hello: () => ({
    output: ASCII_ART.map(line => `\x1b[36m${line}\x1b[0m`).join("\r\n") + "\r\n\x1b[2m// Turn any API into a CLI & MCP Server — v0.1.0\x1b[0m",
    isAscii: true,
  }),

  help: () => ({
    output: [
      "\x1b[36mAvailable commands:\x1b[0m",
      "  genalpha --help    Show usage",
      "  genalpha parse     Parse a repo",
      "  genalpha build     Generate output",
      "  hello              Show banner",
      "  make dev           Start services",
      "  whoami             Who are you?",
      "  ls                 List files",
      "  clear              Clear terminal",
    ].join("\r\n"),
  }),

  "genalpha --help": () => ({
    output: [
      "\x1b[36mgenalpha\x1b[0m — API repos to CLIs & MCP servers",
      "",
      "\x1b[37mUSAGE:\x1b[0m",
      "  genalpha parse <github-url>",
      "  genalpha build <graph.json>",
      "",
      "\x1b[37mOPTIONS:\x1b[0m",
      "  --type cli    --type mcp    --type cli --type mcp",
    ].join("\r\n"),
  }),

  "genalpha parse": () => ({
    output: [
      "\x1b[32m✓\x1b[0m Cloned repository",
      "\x1b[32m✓\x1b[0m Detected FastAPI",
      "\x1b[32m✓\x1b[0m Parsed \x1b[36m23 routes\x1b[0m in \x1b[36m39ms\x1b[0m",
      "\x1b[32m✓\x1b[0m Saved to graph.json",
    ].join("\r\n"),
  }),

  "genalpha build": () => ({
    output: [
      "\x1b[32m✓\x1b[0m Generated CLI → dist/myapi/",
      "\x1b[32m✓\x1b[0m Generated MCP → dist/myapi_mcp/",
      "\x1b[32m✓\x1b[0m Registered with Claude Desktop",
    ].join("\r\n"),
  }),

  whoami: () => ({
    output: "\x1b[36mA developer who ships.\x1b[0m",
  }),

  ls: () => ({
    output: "\x1b[34msrc/\x1b[0m  \x1b[34mweb/\x1b[0m  \x1b[34mservices/\x1b[0m  \x1b[34mworker/\x1b[0m  Makefile  README.md",
  }),

  "make dev": () => ({
    output: [
      "\x1b[32m●\x1b[0m Core API       \x1b[2m:8000\x1b[0m",
      "\x1b[32m●\x1b[0m TPS API        \x1b[2m:8001\x1b[0m",
      "\x1b[32m●\x1b[0m Worker         \x1b[2mparse + generate\x1b[0m",
      "\x1b[32m●\x1b[0m Frontend       \x1b[2m:3000\x1b[0m",
      "",
      "\x1b[36;1mReady!\x1b[0m Open http://localhost:3000",
    ].join("\r\n"),
  }),
};

export function resolveCommand(input: string): CommandResult | null {
  const trimmed = input.trim().toLowerCase();
  if (!trimmed) return null;
  if (trimmed === "clear") return { output: "__CLEAR__" };

  // Exact match
  if (COMMANDS[trimmed]) return COMMANDS[trimmed]();

  // Prefix match for genalpha parse <url>
  if (trimmed.startsWith("genalpha parse ")) return COMMANDS["genalpha parse"]();
  if (trimmed.startsWith("genalpha build")) return COMMANDS["genalpha build"]();

  return {
    output: `\x1b[31mcommand not found:\x1b[0m ${input}\r\n\x1b[2mTry: help, hello, genalpha --help\x1b[0m`,
  };
}
