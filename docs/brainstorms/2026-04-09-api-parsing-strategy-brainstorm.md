# API Parsing Strategy Brainstorm

**Date:** 2026-04-09
**Status:** Decided

## What We're Building

A layered parser pipeline that converts API repositories into a command graph JSON. The system clones a GitHub repo, detects the framework, and runs a chain of parsers in priority order to extract API routes, methods, parameters, and metadata — then outputs the structured command graph that powers CLI generation.

## Target Scope

- **Languages:** Python, Java
- **Frameworks:** FastAPI, Django, Flask (Python) | Spring Boot (Java)
- **Repo access:** GitHub URL (clone remotely)
- **Parse mode:** Static analysis first, runtime extraction optional
- **LLM role:** Enhancement/fallback only, not primary

## Chosen Approach: Layered Parser Pipeline

Four parsing layers run in priority order. Each layer fills gaps the previous one missed.

### Layer 1: OpenAPI/Swagger Spec Detection

- Scan the cloned repo for known spec files: `openapi.json`, `openapi.yaml`, `swagger.json`, `swagger.yaml`, files in `/docs`, `/api-docs`, `/specs` directories
- If found, parse the spec directly into the command graph JSON
- This is the fastest, most accurate path — many mature repos already have specs checked in
- Use a standard OpenAPI parser library to handle v2 (Swagger) and v3 specs

### Layer 2: Annotation/Decorator Regex Parser

For repos without an OpenAPI spec, pattern-match on framework-specific decorators and annotations:

**Python (FastAPI):**
- `@app.get("/path")`, `@app.post("/path")`, `@router.get("/path")`
- Extract path, HTTP method, function name (becomes command name)
- Parse function signature for query params, path params, request body type hints

**Python (Django):**
- `path("route/", view_function)` in `urls.py`
- `@api_view(["GET"])` decorators in DRF
- Class-based views: `class UserViewSet(ModelViewSet)`

**Python (Flask):**
- `@app.route("/path", methods=["GET"])`
- Blueprint route decorators

**Java (Spring Boot):**
- `@RestController`, `@Controller` class-level annotations
- `@GetMapping("/path")`, `@PostMapping("/path")`, `@RequestMapping`
- `@PathVariable`, `@RequestParam`, `@RequestBody` for parameter extraction
- `@RequestMapping` at class level for route prefixes

This layer handles 80%+ of standard repos where routes are declared with simple, direct decorators/annotations.

### Layer 3: AST Parser

For cases where regex fails — composed routes, dynamic paths, variables as route strings, nested router includes:

- **Python:** Use Python's built-in `ast` module to parse source files into syntax trees, then walk the tree to resolve variable references, string concatenation in paths, router prefix composition
- **Java:** Use a Java parser (e.g., `javalang` Python library or tree-sitter Java grammar) to handle annotation attribute resolution, inherited mappings, class-level prefix + method-level path composition

This layer catches the ~15% of cases that use patterns like:
```python
PREFIX = "/api/v1"
app.include_router(user_router, prefix=PREFIX)
```
```java
@RequestMapping("${api.prefix}/users")  // property-based paths
```

### Layer 4: LLM Fallback

For the remaining ~5% that structured parsing can't handle:

- Collect unparsed source files that look like they contain API routes (heuristic: imports from web frameworks, HTTP method keywords)
- Send to an LLM with a structured prompt + the target JSON schema
- Validate LLM output against the command graph schema
- Flag low-confidence extractions for user review

### Pipeline Flow

```
Clone Repo
    |
    v
Detect Framework (scan imports, config files, build files)
    |
    v
[Layer 1] OpenAPI spec found? --> Parse spec --> Done
    |  (no)
    v
[Layer 2] Regex parse decorators/annotations --> Partial result
    |
    v
[Layer 3] AST parse unresolved/complex routes --> Merge results
    |
    v
[Layer 4] LLM fallback for remaining gaps --> Merge results
    |
    v
Validate & Output Command Graph JSON
```

## Key Decisions

1. **Layered pipeline over single-strategy** — deterministic for common cases, graceful degradation for edge cases
2. **Static analysis first** — no need to install deps or run the app; runtime extraction is opt-in for users with a running instance
3. **Regex before AST** — regex is faster and simpler for the 80% case; AST is reserved for complex patterns
4. **LLM as fallback, not primary** — keeps the tool fast, free of API key requirements for common repos, and deterministic
5. **Python + Java (Spring Boot) as initial targets** — covers the two most common enterprise API stacks
6. **GitHub clone as repo access** — no local path support in v1

## Resolved Questions

1. **Framework detection strategy** — Three-step approach: (a) Use GitHub API `/repos/{owner}/{repo}/languages` endpoint to get language breakdown from the repo URL before cloning, (b) scan dependency files (`requirements.txt`, `pyproject.toml`, `pom.xml`, `build.gradle`) after cloning, (c) verify with import scanning in source files if ambiguous.
2. **Handling monorepos** — Generate one CLI with grouped subcommands per service (e.g., `mycli auth login`, `mycli billing list`). Merge all detected services under one command graph.
3. **Nested/grouped routes** — Configurable by user. Default nesting depth provided, but users can adjust during the customization step.
4. **Conflict resolution between layers** — Later layer wins. AST results override regex results for the same route, since AST parsing is structurally more accurate. LLM results override AST if validated.

5. **Parameter type mapping** — Fixed mapping table for common types:

| Python Type | Java Type | CLI Flag Behavior |
|---|---|---|
| `str` | `String` | `--flag VALUE` (string) |
| `int` | `Integer`/`int` | `--flag N` (integer) |
| `bool` | `Boolean`/`boolean` | `--flag` (toggle, no value) |
| `float` | `Double`/`double` | `--flag N.N` (decimal) |
| `List[str]` | `List<String>` | `--flag a,b,c` (comma-separated) |
| `Optional[X]` | `@Nullable X` | Flag is not required |
| `UploadFile` | `MultipartFile` | `--flag @filepath` (file upload) |

Unknown/complex types (Pydantic models, custom enums) are treated as JSON string input for v1.
