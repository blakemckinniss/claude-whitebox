---
description: 📦 Smart Commit - Stage, commit all changes, offer push
argument-hint: [message]
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion
---

Commit all uncommitted changes with a smart commit message, then offer to push.

## Process

1. **Assess Current State**
   ```bash
   git status --porcelain
   git diff --stat
   ```

2. **Run Pre-commit Checks**
   - Execute `upkeep` to ensure code quality
   - If upkeep fails on critical issues, fix them first

3. **Generate Commit Message**
   - If `$ARGUMENTS` provided, use as commit message
   - Otherwise, analyze changes and generate a descriptive message:
     - Prefix: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:` as appropriate
     - Brief summary of what changed and why

4. **Stage and Commit**
   ```bash
   git add -A
   git commit -m "<message>"
   ```

5. **On Success - Offer Push**
   - Use AskUserQuestion: "Push to origin?"
   - Options: "Yes, push now" / "No, just commit"
   - If yes: `git push`

6. **Report**
   ```
   ✅ Committed: <short hash> <message>
   📁 Files: <count> changed
   🚀 Pushed: [yes/no]
   ```

## Rules
- Never force push without explicit SUDO
- If there are no changes, report "Nothing to commit" and exit
- Include `Co-Authored-By: Claude <noreply@anthropic.com>` in commit message
