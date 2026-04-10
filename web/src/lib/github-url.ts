/**
 * Validate and parse a GitHub repository URL.
 * Strict validation: only https://github.com/{owner}/{repo} format.
 * Prevents SSRF by rejecting non-GitHub URLs.
 */

const GITHUB_URL_PATTERN =
  /^https:\/\/github\.com\/([a-zA-Z0-9._-]+)\/([a-zA-Z0-9._-]+)\/?$/;

export interface ParsedGitHubUrl {
  owner: string;
  repo: string;
}

export function parseGitHubUrl(url: string): ParsedGitHubUrl | null {
  const trimmed = url.trim();
  const match = trimmed.match(GITHUB_URL_PATTERN);

  if (!match) return null;

  const [, owner, repo] = match;

  // Reject path traversal attempts
  if (owner.includes("..") || repo.includes("..")) return null;

  // Strip .git suffix if present
  const cleanRepo = repo.replace(/\.git$/, "");

  return { owner, repo: cleanRepo };
}

export function isValidGitHubUrl(url: string): boolean {
  return parseGitHubUrl(url) !== null;
}
