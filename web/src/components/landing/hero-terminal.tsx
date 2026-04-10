"use client";

import { useEffect, useRef, useCallback } from "react";
import { resolveCommand } from "./ascii-banner";

export function HeroTerminal() {
  const termRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<any>(null);
  const inputBuffer = useRef("");
  const historyRef = useRef<string[]>([]);
  const historyIndex = useRef(-1);

  const writePrompt = useCallback(() => {
    if (!xtermRef.current) return;
    const t = xtermRef.current;
    t.write("\x1b[32mnandish\x1b[0m\x1b[2m@\x1b[0m\x1b[36mgenalpha\x1b[0m\x1b[2m:\x1b[0m\x1b[35m~\x1b[0m\x1b[36m$ \x1b[0m");
  }, []);

  const handleCommand = useCallback((cmd: string) => {
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
    let fitAddon: any;

    async function init() {
      const { Terminal } = await import("@xterm/xterm");
      const { FitAddon } = await import("@xterm/addon-fit");
      await import("@xterm/xterm/css/xterm.css");

      terminal = new Terminal({
        theme: {
          background: "#0a0a0e",
          foreground: "#e4e4e7",
          cursor: "#14b8a6",
          cursorAccent: "#0a0a0e",
          selectionBackground: "#14b8a640",
          black: "#050507",
          red: "#f43f5e",
          green: "#22c55e",
          yellow: "#f59e0b",
          blue: "#3b82f6",
          magenta: "#8b5cf6",
          cyan: "#06b6d4",
          white: "#e4e4e7",
          brightBlack: "#3f3f46",
          brightRed: "#fb7185",
          brightGreen: "#4ade80",
          brightYellow: "#fbbf24",
          brightBlue: "#60a5fa",
          brightMagenta: "#a78bfa",
          brightCyan: "#22d3ee",
          brightWhite: "#fafafa",
        },
        fontSize: 13,
        fontFamily: "var(--font-jetbrains-mono), 'JetBrains Mono', monospace",
        cursorBlink: true,
        cursorStyle: "block",
        scrollback: 200,
        allowProposedApi: true,
      });

      fitAddon = new FitAddon();
      terminal.loadAddon(fitAddon);
      terminal.open(termRef.current!);
      fitAddon.fit();

      xtermRef.current = terminal;

      // Write initial prompt
      writePrompt();

      // Handle key input
      terminal.onKey(({ key, domEvent }: { key: string; domEvent: KeyboardEvent }) => {
        const code = domEvent.keyCode;

        if (code === 13) {
          // Enter
          terminal.write("\r\n");
          handleCommand(inputBuffer.current);
          inputBuffer.current = "";
        } else if (code === 8) {
          // Backspace
          if (inputBuffer.current.length > 0) {
            inputBuffer.current = inputBuffer.current.slice(0, -1);
            terminal.write("\b \b");
          }
        } else if (code === 38) {
          // Arrow Up
          if (historyIndex.current > 0) {
            // Clear current input
            const clearLen = inputBuffer.current.length;
            terminal.write("\b \b".repeat(clearLen));
            historyIndex.current--;
            inputBuffer.current = historyRef.current[historyIndex.current];
            terminal.write(inputBuffer.current);
          }
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
        } else if (key.length === 1 && !domEvent.ctrlKey && !domEvent.metaKey) {
          // Regular character
          inputBuffer.current += key;
          terminal.write(key);
        } else if (domEvent.ctrlKey && domEvent.key === "l") {
          // Ctrl+L = clear
          terminal.clear();
          terminal.write("\x1b[2J\x1b[H");
          writePrompt();
          inputBuffer.current = "";
        }
      });

      // Auto-play "hello" after delay
      setTimeout(() => {
        const helloCmd = "hello";
        for (let i = 0; i < helloCmd.length; i++) {
          setTimeout(() => {
            terminal.write(helloCmd[i]);
            inputBuffer.current += helloCmd[i];
            if (i === helloCmd.length - 1) {
              setTimeout(() => {
                terminal.write("\r\n");
                handleCommand(inputBuffer.current);
                inputBuffer.current = "";
              }, 200);
            }
          }, i * 80);
        }
      }, 1500);

      // Resize on window resize
      const resizeHandler = () => fitAddon?.fit();
      window.addEventListener("resize", resizeHandler);

      return () => {
        window.removeEventListener("resize", resizeHandler);
        terminal.dispose();
      };
    }

    init();

    return () => {
      terminal?.dispose();
    };
  }, [handleCommand, writePrompt]);

  return (
    <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg overflow-hidden shadow-[0_40px_100px_rgba(0,0,0,0.6),0_0_0_1px_rgba(255,255,255,0.02)_inset] transition-transform duration-300 hover:-translate-y-1 hover:shadow-[0_50px_120px_rgba(0,0,0,0.7)]">
      {/* Terminal bar */}
      <div className="flex items-center gap-2 px-4 py-3 bg-[var(--elevated)] border-b border-[var(--border)]">
        <div className="w-[11px] h-[11px] rounded-full bg-[#ef4444] opacity-70" />
        <div className="w-[11px] h-[11px] rounded-full bg-[#eab308] opacity-70" />
        <div className="w-[11px] h-[11px] rounded-full bg-[#22c55e] opacity-70" />
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-[var(--text-muted)] ml-auto tracking-wider">
          nandish@genalpha ~/projects
        </span>
      </div>
      {/* Terminal body */}
      <div ref={termRef} className="min-h-[340px]" style={{ padding: "4px" }} />
    </div>
  );
}
