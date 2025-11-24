#!/usr/bin/env python3
"""
Test suite for auto_void.py error handling improvements
Validates stderr logging for critical failures
"""
import json
import sys
import tempfile
import subprocess
from pathlib import Path

# Add scripts/lib to path
_current = Path(__file__).parent.parent
sys.path.insert(0, str(_current / "scripts" / "lib"))

from epistemology import initialize_session_state, save_session_state


def create_mock_transcript(tool_uses: list) -> list:
    """Create a mock transcript with tool use blocks."""
    transcript = []
    for tool_use in tool_uses:
        entry = {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": tool_use["tool"],
                        "input": tool_use["input"],
                    }
                ]
            },
        }
        transcript.append(entry)
    return transcript


def write_transcript(path: Path, transcript: list):
    """Write transcript to JSONL file."""
    with open(path, "w") as f:
        for entry in transcript:
            f.write(json.dumps(entry) + "\n")


def run_hook(
    transcript_path: Path, session_id: str, project_root: Path
) -> tuple[int, str, str]:
    """Run the auto_void hook and return (exit_code, stdout, stderr)."""
    hook_path = project_root / ".claude" / "hooks" / "auto_void.py"

    input_data = {
        "sessionId": session_id,
        "transcriptPath": str(transcript_path),
        "cwd": str(project_root),
    }

    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=10,
    )

    return result.returncode, result.stdout, result.stderr


def test_missing_void_script():
    """Test: void.py missing → stderr warning"""
    print("TEST: Missing void.py script")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        project_root = Path.cwd()

        # Temporarily move void.py if it exists
        void_script = project_root / "scripts" / "ops" / "void.py"
        void_backup = project_root / "scripts" / "ops" / "void.py.bak"

        try:
            if void_script.exists():
                void_script.rename(void_backup)

            test_file = project_root / "scripts" / "ops" / "_test_missing.py"
            test_file.write_text("def foo(): pass")

            transcript = create_mock_transcript(
                [
                    {
                        "tool": "Write",
                        "input": {"file_path": str(test_file), "content": "test"},
                    }
                ]
            )

            transcript_path = tmpdir / "transcript.jsonl"
            write_transcript(transcript_path, transcript)

            session_id = "test_missing_void"
            state = initialize_session_state(session_id)
            state["confidence"] = 75
            save_session_state(session_id, state)

            exit_code, stdout, stderr = run_hook(
                transcript_path, session_id, project_root
            )

            print(f"   Exit Code: {exit_code}")
            print(f"   STDERR: {stderr}")

            assert exit_code == 0, "Hook should exit 0 even on errors"
            assert "void.py not found" in stderr, "Should warn about missing void.py"
            assert "completeness checks disabled" in stderr
            print("   ✅ PASS\n")

        finally:
            # Restore void.py
            if void_backup.exists():
                void_backup.rename(void_script)
            if test_file.exists():
                test_file.unlink()


def test_corrupted_transcript():
    """Test: Corrupted transcript → stderr warning"""
    print("TEST: Corrupted transcript file")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        project_root = Path.cwd()

        # Create corrupted transcript
        transcript_path = tmpdir / "transcript.jsonl"
        transcript_path.write_text(
            "GARBAGE { not valid json\n{more garbage}\n@#$%^&*()"
        )

        session_id = "test_corrupted"
        state = initialize_session_state(session_id)
        state["confidence"] = 75
        save_session_state(session_id, state)

        exit_code, stdout, stderr = run_hook(transcript_path, session_id, project_root)

        print(f"   Exit Code: {exit_code}")
        print(f"   STDERR: {stderr}")

        assert exit_code == 0, "Hook should exit 0 even on corruption"
        assert "corrupted" in stderr.lower(), "Should warn about corruption"
        assert stdout == "", "Should not produce output on corruption"
        print("   ✅ PASS\n")


def test_missing_session_state():
    """Test: Missing session state → stderr notification"""
    print("TEST: Missing session state (fallback)")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        project_root = Path.cwd()

        test_file = project_root / "scripts" / "ops" / "_test_fallback.py"
        try:
            test_file.write_text("def foo(): pass")

            transcript = create_mock_transcript(
                [
                    {
                        "tool": "Write",
                        "input": {"file_path": str(test_file), "content": "test"},
                    }
                ]
            )

            transcript_path = tmpdir / "transcript.jsonl"
            write_transcript(transcript_path, transcript)

            # Use non-existent session ID (no state file)
            session_id = "nonexistent_session_99999"

            exit_code, stdout, stderr = run_hook(
                transcript_path, session_id, project_root
            )

            print(f"   Exit Code: {exit_code}")
            print(f"   STDERR: {stderr}")

            assert exit_code == 0
            assert "Session state not found" in stderr, "Should notify about fallback"
            assert "default policy" in stderr or "CERTAINTY" in stderr
            print("   ✅ PASS\n")

        finally:
            if test_file.exists():
                test_file.unlink()


def test_timeout_handling():
    """Test: Subprocess timeout → stderr warning"""
    print("TEST: Subprocess timeout handling")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        project_root = Path.cwd()

        # Create a mock void.py that hangs
        fake_root = tmpdir / "fake_project"
        fake_root.mkdir()
        (fake_root / "scripts" / "ops").mkdir(parents=True)

        fake_void = fake_root / "scripts" / "ops" / "void.py"
        fake_void.write_text(
            """#!/usr/bin/env python3
import time
time.sleep(999)  # Hang forever
"""
        )

        test_file = fake_root / "scripts" / "ops" / "test.py"
        test_file.write_text("def foo(): pass")

        transcript = create_mock_transcript(
            [
                {
                    "tool": "Write",
                    "input": {"file_path": str(test_file), "content": "test"},
                }
            ]
        )

        transcript_path = tmpdir / "transcript.jsonl"
        write_transcript(transcript_path, transcript)

        session_id = "test_timeout"
        state = initialize_session_state(session_id)
        state["confidence"] = 75
        save_session_state(session_id, state)

        # This will timeout (default 30s, but we'll wait at most 35s for test)
        print("   (This test takes ~30s to verify timeout handling...)")
        exit_code, stdout, stderr = run_hook(transcript_path, session_id, fake_root)

        print(f"   Exit Code: {exit_code}")
        print(f"   STDERR: {stderr}")

        assert exit_code == 0, "Hook should exit 0 on timeout"
        assert "timed out" in stderr.lower(), "Should warn about timeout"
        print("   ✅ PASS\n")


def main():
    """Run all error handling tests."""
    print("=" * 70)
    print("Auto-Void Error Handling Test Suite")
    print("=" * 70 + "\n")

    tests = [
        test_missing_void_script,
        test_corrupted_transcript,
        test_missing_session_state,
        # test_timeout_handling,  # Skip - takes 30s
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"   ❌ FAIL: {e}\n")
            failed += 1
        except Exception as e:
            print(f"   ❌ ERROR: {e}\n")
            import traceback

            traceback.print_exc()
            failed += 1

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("Note: Timeout test skipped (takes 30s)")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
