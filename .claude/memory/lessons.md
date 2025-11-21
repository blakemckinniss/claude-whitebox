# The Pain Log (Lessons Learned)

Document failures, bugs, and wrong assumptions to prevent repeating mistakes.

## Path Resolution

### 2025-11-20: Simple relative paths break in subdirectories
**Problem:** Initial scaffolder used `../lib` for imports, failed for scripts in `scripts/category/`.
**Solution:** Implemented tree-walking to find project root by searching for `scripts/lib/core.py`.
**Lesson:** Never assume script location depth. Always search upward for anchor files.

## Testing

### 2025-11-20: Indexer test falsely failed on footer text
**Problem:** Test checked if "index.py" existed in file, but it appeared in footer "Last updated by scripts/index.py".
**Solution:** Extract only table section for assertions, ignore metadata.
**Lesson:** When testing generated output, isolate the actual content from metadata.

## API Integration

### 2025-11-20: Dry-run checks must come before API key validation
**Problem:** `research.py` and `consult.py` initially checked API keys before checking dry-run flag.
**Solution:** Move dry-run check before API key requirement.
**Lesson:** Allow dry-run to work without credentials for testing.

## Environment Management

### 2025-11-20: System-managed Python environments reject pip install
**Problem:** WSL2 Debian uses externally-managed Python, blocks `pip install`.
**Solution:** Check if packages already installed system-wide before attempting pip.
**Lesson:** Gracefully detect and adapt to system-managed environments.

## Performance

### 2025-11-20: Single-threaded batch operations are unacceptably slow
**Problem:** Processing 100+ files sequentially takes minutes.
**Solution:** Implemented `scripts/lib/parallel.py` with ThreadPoolExecutor.
**Lesson:** For 3+ items, always use parallel execution. Users notice performance.

---
*Add new lessons immediately after encountering the problem. Fresh pain = clear memory.*

### 2025-11-20 16:57
The Elephant Protocol provides persistent memory across sessions using markdown files

### 2025-11-20 20:50
Test lesson from auto-remember hook verification

### 2025-11-20 20:53
Auto-remember Stop hook requires Claude Code restart to activate. Settings.json changes are loaded at startup, not runtime. Hook tested manually and works—extracts Memory Triggers and executes remember.py automatically.

### 2025-11-20 20:54
Auto-remember Stop hook transcript parsing was broken - looked for message.role instead of entry.type at top level. Fixed to parse Claude Code's actual transcript format: entry.type=='assistant' then entry.message.content[].text

### 2025-11-20 20:56
Auto-remember Stop hook debugging - added comprehensive logging to diagnose why hook isn't firing. Logs input, transcript parsing, message extraction, regex matching, and execution to debug_auto_remember.log file.

### 2025-11-20 20:57
Testing auto-remember Stop hook after restart with debug logging enabled. This should automatically execute and appear in lessons.md without manual intervention.

### 2025-11-20 20:58
...

### 2025-11-20 20:58
Auto-remember Stop hook is fully functional. Debug log confirmed successful execution: parses transcript, extracts Memory Triggers, executes remember.py, saves to lessons.md. Switched back to production version without debug logging.

### 2025-11-20 20:59
Auto-remember Stop hook FINAL VERIFICATION TEST at 2025-11-20 21:00 UTC - This unique timestamped lesson confirms the hook is executing automatically without manual intervention. Test ID: UNIQUE-HOOK-TEST-001
