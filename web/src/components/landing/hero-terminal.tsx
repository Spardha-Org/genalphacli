"use client";

import { useEffect, useRef, useCallback } from "react";
import { resolveCommand } from "./ascii-banner";

export function HeroTerminal() {
  const termRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<any>(null);
  const inputBuffer = useRef("");
  const historyRef = useRef<string[]>([]);
  const historyIndex = useRef(-1);
  const autoPlaying = useRef(false);

  const writePrompt = useCallback(() => {
    const t = xtermRef.current;
    if (!t) return;
    t.write("\x1b[32mnandish\x1b[0m\x1b[2m@\x1b[0m\x1b[36mgenalpha\x1b[0m\x1b[2m:\x1b[0m\x1b[35m~\x1b[0m\x1b[36m$ \x1b[0m");
  }, []);

  const runCommand = useCallback((cmd: string) => {
    const t = xtermRef.current;
    if (!t) return;

    if (cmd.trim()) {
      historyRef.current.push(cmd);
      historyIndex.current = historyRef.current.length;
    }

    const result = resolveCommand(cmd);
    if (!result) {
      writePrompt();
      return;
    }
    if (result.output === "__CLEAR__") {
      t.clear();
      t.write("\x1b[2J\x1b[H");
      writePrompt();
      return;
    }
    t.write("\r\n" + result.output + "\r\n");
    writePrompt();
  }, [writePrompt]);

  useEffect(() => {
    if (!termRef.current) return;

    let terminal: any;
    let disposed = false;

    async function init() {
      const { Terminal } = await import("@xterm/xterm");
      const { FitAddon } = await import("@xterm/addon-fit");
      await import("@xterm/xterm/css/xterm.css");

      if (disposed) return;

      terminal = new Terminal({
        theme: {
          background: "#0a0a0e",
          foreground: "#e4e4e7",
          cursor: "#14b8a6",
          cursorAccent: "#0a0a0e",
          selectionBackground: "#14b8a640",
          black: "#050507", red: "#f43f5e", green: "#22c55e", yellow: "#f59e0b",
          blue: "#3b82f6", magenta: "#8b5cf6", cyan: "#14b8a6", white: "#e4e4e7",
          brightBlack: "#3f3f46", brightRed: "#fb7185", brightGreen: "#4ade80",
          brightYellow: "#fbbf24", brightBlue: "#60a5fa", brightMagenta: "#a78bfa",
          brightCyan: "#2dd4bf", brightWhite: "#fafafa",
        },
        fontSize: 13,
        fontFamily: "'JetBrains Mono', monospace",
        cursorBlink: true,
        cursorStyle: "block",
        scrollback: 200,
        disableStdin: false,
      });

      const fitAddon = new FitAddon();
      terminal.loadAddon(fitAddon);
      terminal.open(termRef.current!);
      fitAddon.fit();
      xtermRef.current = terminal;

      writePrompt();

      // Use onData for all input — gives us raw characters
      terminal.onData((data: string) => {
        if (autoPlaying.current) return;

        for (const char of data) {
          if (char === "\r") {
            // Enter
            terminal.write("\r\n");
            runCommand(inputBuffer.current);
            inputBuffer.current = "";
          } else if (char === "\x7f" || char === "\b") {
            // Backspace
            if (inputBuffer.current.length > 0) {
              inputBuffer.current = inputBuffer.current.slice(0, -1);
              terminal.write("\b \b");
            }
          } else if (char === "\x1b[A") {
            // Arrow up (won't hit here as single chars)
          } else if (char >= " " && char <= "~") {
            // Printable ASCII
            inputBuffer.current += char;
            terminal.write(char);
          }
        }
      });

      // Handle arrow keys via onKey (onData doesn't give clean arrow key codes)
      terminal.onKey(({ domEvent }: { key: string; domEvent: KeyboardEvent }) => {
        if (autoPlaying.current) return;
        const code = domEvent.keyCode;

        if (code === 38) {
          // Arrow Up
          if (historyIndex.current > 0) {
            const clearLen = inputBuffer.current.length;
            terminal.write("\b \b".repeat(clearLen));
            historyIndex.current--;
            inputBuffer.current = historyRef.current[historyIndex.current];
            terminal.write(inputBuffer.current);
          }
          domEvent.preventDefault();
        } else if (code === 40) {
          // Arrow Down
          const clearLen = inputBuffer.current.length;
          terminal.write("\b \b".repeat(clearLen));
          if (historyIndex.current < historyRef.current.length - 1) {
            historyIndex.current++;
            inputBuffer.current = historyRef.current[historyIndex.current];
            terminal.write(inputBuffer.current);
          } else {
            historyIndex.current = historyRef.current.length;
            inputBuffer.current = "";
          }
          domEvent.preventDefault();
        } else if (domEvent.ctrlKey && domEvent.key === "l") {
          terminal.clear();
          terminal.write("\x1b[2J\x1b[H");
          writePrompt();
          inputBuffer.current = "";
          domEvent.preventDefault();
        }
      });

      // Auto-play "hello" with typing effect
      setTimeout(() => {
        if (disposed) return;
        autoPlaying.current = true;
        const cmd = "hello";
        for (let i = 0; i < cmd.length; i++) {
          setTimeout(() => {
            if (disposed) return;
            terminal.write(cmd[i]);
            inputBuffer.current += cmd[i];
            if (i === cmd.length - 1) {
              setTimeout(() => {
                if (disposed) return;
                terminal.write("\r\n");
                runCommand(inputBuffer.current);
                inputBuffer.current = "";
                autoPlaying.current = false;
              }, 300);
            }
          }, i * 100);
        }
      }, 1500);

      const onResize = () => fitAddon.fit();
      window.addEventListener("resize", onResize);
      return () => window.removeEventListener("resize", onResize);
    }

    init();
    return () => { disposed = true; terminal?.dispose(); };
  }, [runCommand, writePrompt]);

  return (
    <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg overflow-hidden shadow-[0_40px_100px_rgba(0,0,0,0.6),0_0_0_1px_rgba(255,255,255,0.02)_inset] transition-transform duration-300 hover:-translate-y-1">
      <div className="flex items-center gap-2 px-4 py-3 bg-[var(--elevated)] border-b border-[var(--border)]">
        <div className="w-[11px] h-[11px] rounded-full bg-[#ef4444] opacity-70" />
        <div className="w-[11px] h-[11px] rounded-full bg-[#eab308] opacity-70" />
        <div className="w-[11px] h-[11px] rounded-full bg-[#22c55e] opacity-70" />
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-[var(--text-muted)] ml-auto tracking-wider">
          nandish@genalpha ~/projects
        </span>
      </div>
      <div ref={termRef} className="min-h-[300px] max-h-[420px]" style={{ padding: "4px" }} />
    </div>
  );
}
