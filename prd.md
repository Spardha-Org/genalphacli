# Product Requirements Document (PRD)

## 1. Product Overview

Build a system that converts any API-based repository into a usable CLI by:

* Detecting APIs from a connected GitHub repository
* Generating a command graph (CLI structure)
* Allowing user customization
* Executing commands via API calls using a thin client

---

## 2. Problem Statement

Developers interact with APIs using tools like Postman or custom scripts, which:

* Lack standardization
* Are not easily shareable
* Are not optimized for automation or AI agents

There is no unified system to:

* Convert APIs into CLI tools automatically
* Standardize usage across teams

---

## 3. Goals

### Primary Goals

* Auto-detect APIs from repositories
* Generate CLI commands
* Enable execution via API calls

### Secondary Goals

* Support authentication
* Enable customization of CLI
* Provide extensibility for agents and MCP

---

## 4. User Flow

1. User connects GitHub repository
2. System detects framework and APIs
3. System extracts API schema
4. System generates CLI command graph
5. User customizes CLI (optional)
6. User provides base URL and auth
7. CLI is generated
8. User executes CLI → API call

---

## 5. System Architecture

### Components

1. Repo Connector
2. API Extractor
3. Command Graph Engine
4. CLI Generator
5. Thin Client (API caller)
6. Config Store

---

## 6. API Detection Strategy

### Priority Order

1. OpenAPI detection (/openapi.json)
2. Framework-based AST parsing

   * FastAPI
   * Django
   * Express
3. User correction layer

---

## 7. Data Model (Command Graph)

```json
{
  "command": "abc",
  "version": "1.0.0",
  "base_url": "https://api.example.com",
  "auth": {
    "type": "bearer",
    "env_var": "ABC_API_KEY"
  },
  "subcommands": [
    {
      "name": "d",
      "description": "Fetch data",
      "method": "GET",
      "endpoint": "/d",
      "params": [
        {
          "name": "db",
          "flag": "--db",
          "type": "boolean"
        }
      ],
      "output": {
        "format": "json"
      }
    }
  ]
}
```

---

## 8. CLI Behavior

Example:

```
abc d --db
```

Execution Flow:

* Parse CLI args
* Map to API request
* Call API
* Display formatted output

---

## 9. Functional Requirements

### Repo Integration

* Connect GitHub repo
* Detect language/framework

### API Extraction

* Parse OpenAPI
* Fallback to AST

### CLI Generation

* Generate commands dynamically
* Map params to flags

### Execution

* Call APIs via HTTP
* Handle errors and responses

### Customization

* Rename commands
* Modify flags

### Authentication

* Support API key / Bearer

---

## 10. Non-Functional Requirements

* Performance: CLI execution < 500ms overhead
* Security: No local arbitrary code execution
* Scalability: Support multiple repos

---

## 11. MVP Scope

### Phase 1

* FastAPI support
* OpenAPI parsing
* CLI generation
* Basic API calling

### Phase 2

* Auth support
* Customization

### Phase 3

* Multi-framework support
* Team sharing

---

## 12. Risks

* Incomplete API detection
* Poor CLI UX
* Authentication complexity

---

## 13. Success Metrics

* Time to generate CLI < 2 minutes
* CLI execution success rate > 90%
* User adoption (repos connected)

---

## 14. Future Scope

* MCP integration
* Agent compatibility
* Marketplace for CLI tools

