---
trigger:
  - word:database
  - word:sql
  - word:query
  - word:migration
  - regex:postgres|sqlite|mysql
---

# Database Patterns

- Always use parameterized queries (never string interpolation)
- Wrap multi-statement operations in transactions
- Add indexes for frequently queried columns
- Use migrations for schema changes, never raw DDL in application code
