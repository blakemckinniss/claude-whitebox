---
trigger:
  - word:api
  - word:endpoint
  - word:rest
  - regex:route|controller|handler
---

# API Guidelines

- Use RESTful conventions (GET=read, POST=create, PUT=update, DELETE=remove)
- Return JSON with consistent structure: `{data: ..., error: null}` or `{data: null, error: {...}}`
- Use appropriate HTTP status codes (200, 201, 400, 404, 500)
- Version APIs in URL path: `/api/v1/...`
