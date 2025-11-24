#!/usr/bin/env python3
"""
Integration test: Simulate a Stop hook invocation with actual files
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


def test_real_production_file():
    """Test with actual production file modification"""
    print("=" * 70)
    print("Integration Test: Real Production File Modification")
    print("=" * 70 + "\n")

    project_root = Path.cwd()

    # Create a test file in scripts/ops/ with stubs
    test_file = project_root / "scripts" / "ops" / "_test_void_integration.py"
    try:
        # Write test file with stubs
        test_file.write_text(
            """#!/usr/bin/env python3
# TODO: Complete this implementation

def foo():
    pass

def bar():
    raise NotImplementedError("Not done yet")
"""
        )

        # Create mock transcript showing Write operation
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            transcript = [
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {"type": "text", "text": "Creating test file..."},
                            {
                                "type": "tool_use",
                                "name": "Write",
                                "input": {
                                    "file_path": str(test_file),
                                    "content": "test",
                                },
                            },
                        ]
                    },
                }
            ]

            for entry in transcript:
                f.write(json.dumps(entry) + "\n")

            transcript_path = Path(f.name)

        # Create session with CERTAINTY confidence
        session_id = "test_integration"
        state = initialize_session_state(session_id)
        state["confidence"] = 75  # CERTAINTY tier
        save_session_state(session_id, state)

        # Run auto_void hook
        hook_path = project_root / ".claude" / "hooks" / "auto_void.py"

        input_data = {
            "sessionId": session_id,
            "transcriptPath": str(transcript_path),
            "cwd": str(project_root),
        }

        print("Running auto_void hook with CERTAINTY confidence (75%)...")
        print(f"Modified file: {test_file.relative_to(project_root)}\n")

        result = subprocess.run(
            [sys.executable, str(hook_path)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10,
        )

        print("Exit Code:", result.returncode)
        print("\nSTDOUT:")
        print(result.stdout)

        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)

        # Verify results
        assert result.returncode == 0, "Hook should always exit 0"
        assert "Auto-Void Check" in result.stdout, "Should show void check header"
        assert (
            "_test_void_integration.py" in result.stdout
        ), "Should mention test file"
        assert "stub(s) detected" in result.stdout, "Should detect stubs"
        assert "TODO" in result.stdout or "Line" in result.stdout, "Should show details"

        print("\n✅ Integration test PASSED")
        print("=" * 70)

        # Cleanup
        transcript_path.unlink()

    finally:
        # Always clean up test file
        if test_file.exists():
            test_file.unlink()


def test_trusted_tier_silent():
    """Test TRUSTED tier: Silent unless issues"""
    print("\n" + "=" * 70)
    print("Integration Test: TRUSTED Tier (Silent Mode)")
    print("=" * 70 + "\n")

    project_root = Path.cwd()

    # Create clean test file
    test_file = project_root / "scripts" / "ops" / "_test_void_clean.py"
    try:
        test_file.write_text(
            """#!/usr/bin/env python3
def clean_function():
    return "complete"
"""
        )

        # Create transcript
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            transcript = [
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Write",
                                "input": {
                                    "file_path": str(test_file),
                                    "content": "test",
                                },
                            }
                        ]
                    },
                }
            ]

            for entry in transcript:
                f.write(json.dumps(entry) + "\n")

            transcript_path = Path(f.name)

        # TRUSTED tier confidence
        session_id = "test_trusted"
        state = initialize_session_state(session_id)
        state["confidence"] = 90  # TRUSTED tier
        save_session_state(session_id, state)

        hook_path = project_root / ".claude" / "hooks" / "auto_void.py"

        input_data = {
            "sessionId": session_id,
            "transcriptPath": str(transcript_path),
            "cwd": str(project_root),
        }

        print("Running auto_void hook with TRUSTED confidence (90%)...")
        print("File is clean, should be silent...\n")

        result = subprocess.run(
            [sys.executable, str(hook_path)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10,
        )

        print("Exit Code:", result.returncode)
        print("STDOUT:", repr(result.stdout))

        assert result.returncode == 0
        assert (
            result.stdout == "" or "Clean" not in result.stdout
        ), "TRUSTED tier should be silent on clean files"

        print("\n✅ TRUSTED tier silent mode PASSED")
        print("=" * 70)

        # Cleanup
        transcript_path.unlink()

    finally:
        if test_file.exists():
            test_file.unlink()


if __name__ == "__main__":
    try:
        test_real_production_file()
        test_trusted_tier_silent()
        print("\n" + "=" * 70)
        print("ALL INTEGRATION TESTS PASSED")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
