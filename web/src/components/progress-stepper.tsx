"use client";

interface Step {
  key: string;
  label: string;
  description: string;
}

const GITHUB_PARSE_STEPS: Step[] = [
  { key: "cloning", label: "Cloning repository", description: "Downloading from GitHub..." },
  { key: "parsing", label: "Parsing routes", description: "Extracting API routes via static analysis..." },
  { key: "parsed", label: "Done", description: "Routes parsed successfully." },
];

const PYPI_PARSE_STEPS: Step[] = [
  { key: "downloading", label: "Downloading package", description: "Fetching source distribution from PyPI..." },
  { key: "parsing", label: "Parsing routes", description: "Extracting API routes via static analysis..." },
  { key: "parsed", label: "Done", description: "Routes parsed successfully." },
];

const GENERATE_STEPS: Step[] = [
  { key: "generating", label: "Generating packages", description: "Building CLI and MCP server..." },
  { key: "packaging", label: "Packaging", description: "Creating downloadable zip..." },
  { key: "complete", label: "Done", description: "Download ready!" },
];

interface ProgressStepperProps {
  currentStatus: string;
  errorMessage?: string | null;
  mode: "parse" | "generate";
  sourceType?: "github" | "pypi";
}

export function ProgressStepper({ currentStatus, errorMessage, mode, sourceType }: ProgressStepperProps) {
  const steps = mode === "generate"
    ? GENERATE_STEPS
    : sourceType === "pypi"
      ? PYPI_PARSE_STEPS
      : GITHUB_PARSE_STEPS;
  const failed = currentStatus === "failed" || currentStatus === "timed_out";

  const currentStepIndex = steps.findIndex((s) => s.key === currentStatus);
  const activeIndex = failed ? -1 : currentStepIndex;

  return (
    <div className="space-y-4">
      {steps.map((step, i) => {
        const isComplete = i < activeIndex || currentStatus === steps[steps.length - 1].key;
        const isActive = i === activeIndex && !isComplete;
        const isPending = i > activeIndex && !isComplete;

        return (
          <div key={step.key} className="flex items-start gap-4">
            {/* Circle indicator */}
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors ${
                  isComplete
                    ? "bg-teal-500 border-teal-500 text-zinc-950"
                    : isActive
                      ? "border-teal-500 text-teal-500 animate-pulse"
                      : "border-zinc-700 text-zinc-700"
                }`}
              >
                {isComplete ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <span className="text-xs font-mono">{i + 1}</span>
                )}
              </div>
              {i < steps.length - 1 && (
                <div
                  className={`w-0.5 h-8 ${isComplete ? "bg-teal-500" : "bg-zinc-800"}`}
                />
              )}
            </div>

            {/* Step content */}
            <div className="pt-1">
              <p
                className={`text-sm font-medium ${
                  isComplete
                    ? "text-teal-400"
                    : isActive
                      ? "text-zinc-50"
                      : "text-zinc-600"
                }`}
              >
                {step.label}
              </p>
              {isActive && (
                <p className="text-xs text-zinc-500 mt-0.5">{step.description}</p>
              )}
            </div>
          </div>
        );
      })}

      {failed && errorMessage && (
        <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-md">
          <p className="text-sm text-rose-400 font-medium">
            {currentStatus === "timed_out" ? "Timed out" : "Failed"}
          </p>
          <p className="text-xs text-rose-300/70 mt-1 font-mono">{errorMessage}</p>
        </div>
      )}
    </div>
  );
}
