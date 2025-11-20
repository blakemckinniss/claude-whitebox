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
