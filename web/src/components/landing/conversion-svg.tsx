"use client";

export function ConversionSvg() {
  return (
    <svg viewBox="0 0 520 400" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-auto">
      {/* Code Panel (left) */}
      <rect x="10" y="30" width="200" height="340" rx="6" fill="#0a0a0e" stroke="#1a1a22" />
      <rect x="10" y="30" width="200" height="28" rx="6" fill="#0f0f14" />
      <circle cx="26" cy="44" r="4" fill="#ef4444" opacity=".7" />
      <circle cx="38" cy="44" r="4" fill="#eab308" opacity=".7" />
      <circle cx="50" cy="44" r="4" fill="#22c55e" opacity=".7" />
      <text x="80" y="48" fontFamily="JetBrains Mono, monospace" fontSize="8" fill="#3f3f46">api.py</text>

      {/* Animated code lines */}
      <g fontFamily="JetBrains Mono, monospace" fontSize="9">
        <text x="22" y="80" fill="#8b5cf6" opacity="0">
          <animate attributeName="opacity" values="0;1" dur="0.3s" begin="0.5s" fill="freeze" />@app.get
        </text>
        <text x="22" y="95" fill="#71717a" opacity="0">
          <animate attributeName="opacity" values="0;1" dur="0.3s" begin="0.8s" fill="freeze" />def list_users():
        </text>
        <text x="22" y="110" fill="#22c55e" opacity="0">
          <animate attributeName="opacity" values="0;1" dur="0.3s" begin="1.1s" fill="freeze" />{"  return db.all()"}
        </text>
        <text x="22" y="135" fill="#3b82f6" opacity="0">
          <animate attributeName="opacity" values="0;1" dur="0.3s" begin="1.5s" fill="freeze" />@app.post
        </text>
        <text x="22" y="150" fill="#71717a" opacity="0">
          <animate attributeName="opacity" values="0;1" dur="0.3s" begin="1.8s" fill="freeze" />def create_user(body):
        </text>
        <text x="22" y="165" fill="#22c55e" opacity="0">
          <animate attributeName="opacity" values="0;1" dur="0.3s" begin="2.1s" fill="freeze" />{"  return db.create()"}
        </text>
        <text x="22" y="190" fill="#f59e0b" opacity="0">
          <animate attributeName="opacity" values="0;1" dur="0.3s" begin="2.5s" fill="freeze" />@app.delete
        </text>
        <text x="22" y="205" fill="#71717a" opacity="0">
          <animate attributeName="opacity" values="0;1" dur="0.3s" begin="2.8s" fill="freeze" />def del_user(id):
        </text>
        <text x="22" y="250" fill="#3f3f46" opacity="0">
          <animate attributeName="opacity" values="0;1" dur="0.3s" begin="3.5s" fill="freeze" />// 23 more routes...
        </text>
      </g>

      {/* Flow paths */}
      <path id="f1" d="M220,120 C260,120 270,100 310,100" stroke="none" fill="none" />
      <path id="f2" d="M220,180 C260,180 270,200 310,200" stroke="none" fill="none" />

      {/* Visible flow lines */}
      <path d="M220,120 C260,120 270,100 310,100" stroke="#14b8a6" strokeWidth="1" opacity=".2" strokeDasharray="4 4">
        <animate attributeName="strokeDashoffset" from="8" to="0" dur="1s" repeatCount="indefinite" />
      </path>
      <path d="M220,180 C260,180 270,200 310,200" stroke="#3b82f6" strokeWidth="1" opacity=".2" strokeDasharray="4 4">
        <animate attributeName="strokeDashoffset" from="8" to="0" dur="1s" repeatCount="indefinite" />
      </path>

      {/* Flowing dots */}
      <circle r="3" fill="#14b8a6" opacity=".9">
        <animateMotion dur="2s" repeatCount="indefinite"><mpath href="#f1" /></animateMotion>
      </circle>
      <circle r="3" fill="#3b82f6" opacity=".9">
        <animateMotion dur="2.2s" repeatCount="indefinite" begin="0.3s"><mpath href="#f2" /></animateMotion>
      </circle>

      {/* GenAlpha Parser (center) */}
      <rect x="245" y="140" width="70" height="70" rx="4" fill="#0f0f14" stroke="#14b8a6" strokeWidth="1.5" opacity="0">
        <animate attributeName="opacity" values="0;1" dur="0.5s" begin="1.5s" fill="freeze" />
      </rect>
      <text x="253" y="172" fontFamily="JetBrains Mono, monospace" fontSize="7" fill="#14b8a6" opacity="0">
        <animate attributeName="opacity" values="0;1" dur="0.5s" begin="1.5s" fill="freeze" />GENALPHA
      </text>
      <text x="260" y="184" fontFamily="JetBrains Mono, monospace" fontSize="6" fill="#3f3f46" opacity="0">
        <animate attributeName="opacity" values="0;1" dur="0.5s" begin="1.8s" fill="freeze" />PARSER
      </text>

      {/* Spinning indicator */}
      <circle cx="280" cy="196" r="6" fill="none" stroke="#14b8a6" strokeWidth="1" strokeDasharray="8 20" opacity="0">
        <animate attributeName="opacity" values="0;.6" dur="0.3s" begin="2s" fill="freeze" />
        <animateTransform attributeName="transform" type="rotate" from="0 280 196" to="360 280 196" dur="2s" repeatCount="indefinite" />
      </circle>

      {/* CLI Output */}
      <rect x="320" y="60" width="190" height="130" rx="6" fill="#0a0a0e" stroke="#22c55e" strokeWidth="1" opacity="0">
        <animate attributeName="opacity" values="0;1" dur="0.5s" begin="3s" fill="freeze" />
      </rect>
      <text x="334" y="80" fontFamily="JetBrains Mono, monospace" fontSize="8" fontWeight="bold" fill="#22c55e" opacity="0">
        <animate attributeName="opacity" values="0;1" dur="0.5s" begin="3s" fill="freeze" />CLI OUTPUT
      </text>
      <g fontFamily="JetBrains Mono, monospace" fontSize="8" opacity="0">
        <animate attributeName="opacity" values="0;1" dur="0.5s" begin="3.3s" fill="freeze" />
        <text x="330" y="100" fill="#14b8a6">$</text>
        <text x="340" y="100" fill="#e4e4e7">myapi --help</text>
        <text x="330" y="115" fill="#71717a">list-users</text>
        <text x="330" y="130" fill="#71717a">create-user</text>
        <text x="330" y="145" fill="#3f3f46">+ 20 more</text>
      </g>

      {/* MCP Output */}
      <rect x="320" y="210" width="190" height="130" rx="6" fill="#0a0a0e" stroke="#8b5cf6" strokeWidth="1" opacity="0">
        <animate attributeName="opacity" values="0;1" dur="0.5s" begin="3.5s" fill="freeze" />
      </rect>
      <text x="334" y="230" fontFamily="JetBrains Mono, monospace" fontSize="8" fontWeight="bold" fill="#8b5cf6" opacity="0">
        <animate attributeName="opacity" values="0;1" dur="0.5s" begin="3.5s" fill="freeze" />MCP SERVER
      </text>
      <g fontFamily="JetBrains Mono, monospace" fontSize="8" opacity="0">
        <animate attributeName="opacity" values="0;1" dur="0.5s" begin="3.8s" fill="freeze" />
        <text x="330" y="250" fill="#8b5cf6">@mcp.tool()</text>
        <text x="330" y="265" fill="#71717a">list_users()</text>
        <text x="330" y="280" fill="#8b5cf6">@mcp.tool()</text>
        <text x="330" y="295" fill="#71717a">create_user()</text>
      </g>

      {/* Labels */}
      <text x="80" y="20" fontFamily="JetBrains Mono, monospace" fontSize="9" fill="#3f3f46" letterSpacing="2" opacity="0">
        <animate attributeName="opacity" values="0;.6" dur="0.5s" begin="0.3s" fill="freeze" />YOUR API CODE
      </text>
      <text x="370" y="50" fontFamily="JetBrains Mono, monospace" fontSize="9" fill="#3f3f46" letterSpacing="2" opacity="0">
        <animate attributeName="opacity" values="0;.6" dur="0.5s" begin="2.8s" fill="freeze" />GENERATED OUTPUT
      </text>

      {/* Center glow */}
      <circle cx="280" cy="175" r="40" fill="url(#gc)" opacity="0">
        <animate attributeName="opacity" values="0;1" dur="1s" begin="2s" fill="freeze" />
      </circle>
      <defs>
        <radialGradient id="gc">
          <stop offset="0%" stopColor="#14b8a6" stopOpacity=".15" />
          <stop offset="100%" stopColor="#14b8a6" stopOpacity="0" />
        </radialGradient>
      </defs>
    </svg>
  );
}
