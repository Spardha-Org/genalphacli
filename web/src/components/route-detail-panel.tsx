"use client";

interface RouteParam {
  name: string;
  type: string;
  required: boolean;
  description?: string;
}

interface Route {
  name: string;
  description?: string;
  method: string;
  endpoint: string;
  params?: RouteParam[];
  output?: { format?: string; schema?: Record<string, unknown> };
}

const METHOD_COLORS: Record<string, string> = {
  GET: "text-emerald-400",
  POST: "text-blue-400",
  PUT: "text-amber-400",
  DELETE: "text-rose-400",
  PATCH: "text-violet-400",
};

interface RouteDetailPanelProps {
  route: Route;
  onClose: () => void;
}

export function RouteDetailPanel({ route, onClose }: RouteDetailPanelProps) {
  return (
    <div className="w-[360px] border-l border-zinc-800 bg-zinc-900 overflow-y-auto">
      <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
        <h3 className="text-sm font-medium">Route Details</h3>
        <button
          onClick={onClose}
          className="text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Method + Path */}
        <div>
          <span className={`text-xs font-bold ${METHOD_COLORS[route.method.toUpperCase()] || "text-zinc-400"}`}>
            {route.method.toUpperCase()}
          </span>
          <p className="text-sm font-[family-name:var(--font-geist-mono)] text-zinc-200 mt-1">
            {route.endpoint}
          </p>
        </div>

        {/* Description */}
        {route.description && (
          <div>
            <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Description</p>
            <p className="text-sm text-zinc-400">{route.description}</p>
          </div>
        )}

        {/* Parameters */}
        {route.params && route.params.length > 0 && (
          <div>
            <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">
              Parameters ({route.params.length})
            </p>
            <div className="space-y-2">
              {route.params.map((param) => (
                <div
                  key={param.name}
                  className="bg-zinc-800 rounded-md px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-[family-name:var(--font-geist-mono)] text-zinc-200">
                      {param.name}
                    </span>
                    <span className="text-[10px] text-zinc-500 bg-zinc-700 px-1.5 py-0.5 rounded">
                      {param.type}
                    </span>
                    {param.required && (
                      <span className="text-[10px] text-amber-500">required</span>
                    )}
                  </div>
                  {param.description && (
                    <p className="text-[10px] text-zinc-500 mt-1">{param.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Response */}
        {route.output?.format && (
          <div>
            <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Response</p>
            <p className="text-sm text-zinc-400">{route.output.format}</p>
          </div>
        )}
      </div>
    </div>
  );
}
