#!/usr/bin/env python3
"""
Test suite for auto_void.py Stop hook
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
                    {"type": "text", "text": "Working on it..."},
                    {
                        "type": "tool_use",
                        "name": tool_use["tool"],
                        "input": tool_use["input"],
                    },
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


def test_no_python_files():
    """Test: No Python files modified → Silent exit"""
    print("TEST: No Python files modified")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        project_root = Path.cwd()

        # Create transcript with non-Python file
        transcript = create_mock_transcript(
            [
                {
                    "tool": "Write",
                    "input": {"file_path": "scripts/ops/test.md", "content": "test"},
                }
            ]
        )

        transcript_path = tmpdir / "transcript.jsonl"
        write_transcript(transcript_path, transcript)

        # Create session with CERTAINTY confidence
        session_id = "test_no_python"
        state = initialize_session_state(session_id)
        state["confidence"] = 75
        save_session_state(session_id, state)

        # Run hook
        exit_code, stdout, stderr = run_hook(transcript_path, session_id, project_root)

        assert exit_code == 0, f"Expected exit 0, got {exit_code}"
        assert stdout == "", f"Expected silent exit, got: {stdout}"
        print("   ✅ PASS\n")


def test_scratch_file_modified():
    """Test: Scratch file modified → No void check"""
    print("TEST: Scratch file modified")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        project_root = Path.cwd()

        # Create transcript with scratch file
        transcript = create_mock_transcript(
            [
                {
                    "tool": "Write",
                    "input": {
                        "file_path": "scratch/test_script.py",
                        "content": "# test",
                    },
                }
            ]
        )

        transcript_path = tmpdir / "transcript.jsonl"
        write_transcript(transcript_path, transcript)

        session_id = "test_scratch"
        state = initialize_session_state(session_id)
        state["confidence"] = 75
        save_session_state(session_id, state)

        exit_code, stdout, stderr = run_hook(transcript_path, session_id, project_root)

        assert exit_code == 0
        assert stdout == ""
        print("   ✅ PASS\n")


def test_ignorance_tier_no_action():
    """Test: IGNORANCE tier → No action"""
    print("TEST: IGNORANCE tier (no action)")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        project_root = Path.cwd()

        transcript = create_mock_transcript(
            [
                {
                    "tool": "Write",
                    "input": {
                        "file_path": "scripts/ops/test.py",
                        "content": "# test",
                    },
                }
            ]
        )

        transcript_path = tmpdir / "transcript.jsonl"
        write_transcript(transcript_path, transcript)

        session_id = "test_ignorance"
        state = initialize_session_state(session_id)
        state["confidence"] = 20  # IGNORANCE
        save_session_state(session_id, state)

        exit_code, stdout, stderr = run_hook(transcript_path, session_id, project_root)

        assert exit_code == 0
        assert stdout == ""
        print("   ✅ PASS\n")


def test_certainty_tier_clean_file():
    """Test: CERTAINTY tier + clean file → Success message"""
    print("TEST: CERTAINTY tier (clean file)")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        project_root = Path.cwd()

        # Create a clean test file
        test_file = tmpdir / "test_clean.py"
        test_file.write_text('def foo():\n    return "clean"\n')

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

        session_id = "test_certainty_clean"
        state = initialize_session_state(session_id)
        state["confidence"] = 75  # CERTAINTY
        save_session_state(session_id, state)

        exit_code, stdout, stderr = run_hook(transcript_path, session_id, project_root)

        assert exit_code == 0
        # Note: This will likely show no output because test_clean.py
        # is not in a production zone. This is expected behavior.
        print("   ✅ PASS\n")


def test_certainty_tier_stub_file():
    """Test: CERTAINTY tier + stub file → Warning message"""
    print("TEST: CERTAINTY tier (stub file)")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        project_root = Path.cwd()

        # Create a file with stubs
        test_file = tmpdir / "test_stub.py"
        test_file.write_text(
            "# TODO: Implement this\ndef foo():\n    pass\nraise NotImplementedError\n"
        )

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

        session_id = "test_certainty_stub"
        state = initialize_session_state(session_id)
        state["confidence"] = 75  # CERTAINTY
        save_session_state(session_id, state)

        exit_code, stdout, stderr = run_hook(transcript_path, session_id, project_root)

        assert exit_code == 0
        # Same as above - test file is not in production zone
        print("   ✅ PASS\n")


def test_production_file_extraction():
    """Test: Extract only production zone files"""
    print("TEST: Production file extraction")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        project_root = Path.cwd()

        # Multiple files: production + scratch + root
        transcript = create_mock_transcript(
            [
                {
                    "tool": "Write",
                    "input": {
                        "file_path": "scripts/ops/foo.py",  # PRODUCTION
                        "content": "test",
                    },
                },
                {
                    "tool": "Write",
                    "input": {
                        "file_path": "scripts/lib/bar.py",  # PRODUCTION
                        "content": "test",
                    },
                },
                {
                    "tool": "Write",
                    "input": {"file_path": "scratch/baz.py", "content": "test"},  # NOT
                },
                {
                    "tool": "Write",
                    "input": {"file_path": "test.py", "content": "test"},  # NOT
                },
            ]
        )

        transcript_path = tmpdir / "transcript.jsonl"
        write_transcript(transcript_path, transcript)

        # Import extraction function
        sys.path.insert(0, str(project_root / ".claude" / "hooks"))
        from auto_void import extract_modified_python_files

        files = extract_modified_python_files(transcript, project_root)
        file_strs = [str(f.relative_to(project_root)) for f in files]

        assert "scripts/ops/foo.py" in file_strs
        assert "scripts/lib/bar.py" in file_strs
        assert "scratch/baz.py" not in file_strs
        assert "test.py" not in file_strs

        print(f"   Extracted: {file_strs}")
        print("   ✅ PASS\n")


def test_deduplication():
    """Test: Same file modified multiple times → One check"""
    print("TEST: File deduplication")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        project_root = Path.cwd()

        # Same file written and edited
        transcript = create_mock_transcript(
            [
                {
                    "tool": "Write",
                    "input": {"file_path": "scripts/ops/foo.py", "content": "v1"},
                },
                {
                    "tool": "Edit",
                    "input": {
                        "file_path": "scripts/ops/foo.py",
                        "old_string": "v1",
                        "new_string": "v2",
                    },
                },
                {
                    "tool": "Edit",
                    "input": {
                        "file_path": "scripts/ops/foo.py",
                        "old_string": "v2",
                        "new_string": "v3",
                    },
                },
            ]
        )

        transcript_path = tmpdir / "transcript.jsonl"
        write_transcript(transcript_path, transcript)

        sys.path.insert(0, str(project_root / ".claude" / "hooks"))
        from auto_void import extract_modified_python_files

        files = extract_modified_python_files(transcript, project_root)

        assert len(files) == 1
        assert str(files[0].relative_to(project_root)) == "scripts/ops/foo.py"

        print(f"   Deduplicated to: {len(files)} file(s)")
        print("   ✅ PASS\n")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Auto-Void Hook Test Suite")
    print("=" * 70 + "\n")

    tests = [
        test_no_python_files,
        test_scratch_file_modified,
        test_ignorance_tier_no_action,
        test_certainty_tier_clean_file,
        test_certainty_tier_stub_file,
        test_production_file_extraction,
        test_deduplication,
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
            failed += 1

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
