---
trigger:
  - word:test
  - word:testing
  - phrase:unit test
  - regex:pytest|jest|vitest|mocha
---

# Testing Reminders

- Test behavior, not implementation details
- One assertion per test when possible
- Use descriptive test names: `test_<action>_when_<condition>_should_<expected>`
- Mock external dependencies, not internal modules
