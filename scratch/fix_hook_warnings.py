#!/usr/bin/env python3
"""
Batch fix hook warnings:
1. Replace bare 'except:' with 'except Exception:'
2. Add timeout to requests calls
3. Add timeout to subprocess calls
"""

import re
from pathlib import Path

HOOKS_DIR = Path(__file__).parent.parent / ".claude" / "hooks"

def fix_bare_except(content: str) -> tuple[str, int]:
    """Replace bare except: with except Exception:"""
    # Match 'except:' not followed by a type
    pattern = r'\bexcept\s*:'
    matches = list(re.finditer(pattern, content))
    count = len(matches)
    if count > 0:
        content = re.sub(pattern, 'except Exception:', content)
    return content, count

def fix_requests_timeout(content: str) -> tuple[str, int]:
    """Add timeout=10 to requests calls without timeout"""
    count = 0

    # Pattern for requests.get/post/put/delete without timeout
    # Match: requests.get(url) or requests.get(url, params=...) without timeout=
    patterns = [
        # requests.get("url") -> requests.get("url", timeout=10)
        (r'(requests\.(get|post|put|delete|patch|head)\([^)]+)(\))',
         lambda m: m.group(1) + ', timeout=10' + m.group(3) if 'timeout' not in m.group(1) else m.group(0)),
    ]

    for pattern, replacement in patterns:
        new_content, n = re.subn(pattern, replacement, content)
        if n > 0 and 'timeout' not in content.split('requests')[0]:
            count += n
            content = new_content

    return content, count

def fix_subprocess_timeout(content: str) -> tuple[str, int]:
    """Add timeout=30 to subprocess.run calls without timeout"""
    count = 0

    # This is trickier - need to find subprocess.run calls without timeout
    # Simple approach: find subprocess.run( and check if timeout= is in the call

    lines = content.split('\n')
    new_lines = []
    in_subprocess_call = False
    call_lines = []
    paren_depth = 0

    for line in lines:
        if 'subprocess.run(' in line or 'subprocess.check_output(' in line:
            in_subprocess_call = True
            call_lines = [line]
            paren_depth = line.count('(') - line.count(')')
            if paren_depth == 0:
                # Single line call
                full_call = line
                if 'timeout' not in full_call:
                    # Add timeout before closing paren
                    line = re.sub(r'(\s*)\)(\s*)$', r', timeout=30)\2', line)
                    count += 1
                in_subprocess_call = False
                call_lines = []
            new_lines.append(line)
        elif in_subprocess_call:
            call_lines.append(line)
            paren_depth += line.count('(') - line.count(')')
            if paren_depth <= 0:
                # End of call
                full_call = '\n'.join(call_lines)
                if 'timeout' not in full_call:
                    # Add timeout before closing paren on this line
                    line = re.sub(r'(\s*)\)(\s*)$', r', timeout=30)\2', line)
                    count += 1
                in_subprocess_call = False
                call_lines = []
            new_lines.append(line)
        else:
            new_lines.append(line)

    return '\n'.join(new_lines), count

def process_hook(hook_path: Path) -> dict:
    """Process a single hook file"""
    results = {"file": hook_path.name, "changes": []}

    content = hook_path.read_text()
    original = content

    # Fix bare except
    content, n = fix_bare_except(content)
    if n > 0:
        results["changes"].append(f"Fixed {n} bare except clause(s)")

    # Fix requests timeout
    if 'requests.' in content:
        content, n = fix_requests_timeout(content)
        if n > 0:
            results["changes"].append(f"Added timeout to {n} requests call(s)")

    # Fix subprocess timeout
    if 'subprocess.' in content:
        content, n = fix_subprocess_timeout(content)
        if n > 0:
            results["changes"].append(f"Added timeout to {n} subprocess call(s)")

    # Write back if changed
    if content != original:
        hook_path.write_text(content)
        results["modified"] = True
    else:
        results["modified"] = False

    return results

def main():
    print("=" * 60)
    print("🔧 HOOK WARNING FIXER")
    print("=" * 60)

    total_modified = 0
    total_changes = 0

    for hook_path in sorted(HOOKS_DIR.glob("*.py")):
        if hook_path.name.startswith("__"):
            continue
        if "backup" in hook_path.name:
            continue  # Skip backup files
        if hook_path.parent.name == "archive":
            continue  # Skip archived hooks

        result = process_hook(hook_path)

        if result["modified"]:
            total_modified += 1
            total_changes += len(result["changes"])
            print(f"\n✅ {result['file']}:")
            for change in result["changes"]:
                print(f"   • {change}")

    print("\n" + "=" * 60)
    print(f"📊 SUMMARY: Modified {total_modified} files, {total_changes} total changes")
    print("=" * 60)

if __name__ == "__main__":
    main()
