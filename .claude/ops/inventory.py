#!/usr/bin/env python3
"""
The Scanner: Detects available system binaries, languages, and network capabilities
"""
import sys
import os
import shutil
import platform
import subprocess
import socket

# Add .claude/lib to path
_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
# Find project root by looking for '.claude' directory
_current = _script_dir
while _current != "/":
    if os.path.exists(os.path.join(_current, ".claude", "lib", "core.py")):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root with .claude/lib/core.py")
sys.path.insert(0, os.path.join(_project_root, ".claude", "lib"))
from core import setup_script, finalize, logger, handle_debug  # noqa: E402


def check_binary(name):
    """Check if a binary exists in PATH."""
    path = shutil.which(name)
    if path:
        return f"✅ {name:20} ({path})"
    else:
        return f"❌ {name:20} (not found)"


def check_language(name, version_cmd):
    """Check if a language runtime is available and get version."""
    try:
        result = subprocess.run(
            version_cmd, shell=True, capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            version = result.stdout.strip().split("\n")[0]
            return f"✅ {name:20} {version}"
        else:
            return f"❌ {name:20} (not found)"
    except Exception:
        return f"❌ {name:20} (not found)"


def check_network_connectivity():
    """Check basic network connectivity."""
    try:
        # Try to connect to Google DNS
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("8.8.8.8", 53))
        sock.close()
        return "✅ Internet connectivity (tested 8.8.8.8:53)"
    except Exception:
        return "❌ No internet connectivity or blocked"


def main():
    parser = setup_script(
        "The Scanner: Detects available system binaries, languages, and network capabilities"
    )

    parser.add_argument(
        "--compact",
        action="store_true",
        help="Show only available tools (hide unavailable)",
    )

    args = parser.parse_args()
    handle_debug(args)

    if args.dry_run:
        logger.warning("⚠️  DRY RUN MODE: Would scan system capabilities")
        finalize(success=True)

    try:
        print("\n" + "=" * 70)
        print("🕵️  MACGYVER SITREP: System Capability Scan")
        print("=" * 70)

        # System Information
        print("\n📍 SYSTEM INFORMATION")
        print(f"   Hostname:     {platform.node()}")
        print(f"   OS:           {platform.system()} {platform.release()}")
        print(f"   Architecture: {platform.machine()}")
        print(f"   Kernel:       {platform.version()}")

        # User context
        try:
            username = os.getlogin()
        except Exception:
            username = os.environ.get("USER", "unknown")

        uid = os.getuid() if hasattr(os, "getuid") else "N/A"
        is_root = uid == 0 if uid != "N/A" else False

        print(f"   User:         {username} (UID: {uid})")
        print(f"   Privileges:   {'🔴 ROOT' if is_root else '🟢 Non-root'}")

        # Toolbox - Useful system binaries
        print("\n🧰 TOOLBOX (System Binaries)")
        tools = [
            "curl",
            "wget",
            "nc",
            "netcat",
            "telnet",
            "git",
            "docker",
            "jq",
            "yq",
            "awk",
            "sed",
            "grep",
            "perl",
            "ruby",
            "gcc",
            "make",
            "cmake",
            "ffmpeg",
            "imagemagick",
            "convert",
            "zip",
            "unzip",
            "tar",
            "gzip",
            "ssh",
            "scp",
            "rsync",
            "vim",
            "nano",
            "emacs",
        ]

        results = [check_binary(tool) for tool in tools]

        if args.compact:
            for result in results:
                if result.startswith("✅"):
                    print(f"   {result}")
        else:
            for result in results:
                print(f"   {result}")

        # Runtime Languages
        print("\n🐍 RUNTIME LANGUAGES")
        languages = [
            ("Python 3", "python3 --version"),
            ("Python 2", "python2 --version"),
            ("Node.js", "node --version"),
            ("Go", "go version"),
            ("Rust", "rustc --version"),
            ("Java", "java -version 2>&1 | head -1"),
            ("Ruby", "ruby --version"),
            ("PHP", "php --version | head -1"),
        ]

        for name, cmd in languages:
            result = check_language(name, cmd)
            if args.compact and result.startswith("❌"):
                continue
            print(f"   {result}")

        # Network Capabilities
        print("\n🌐 NETWORK CAPABILITIES")
        print(f"   {check_network_connectivity()}")

        # Check for common proxy environment variables
        proxy_vars = ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]
        proxy_found = False
        for var in proxy_vars:
            if os.environ.get(var):
                print(f"   ⚠️  Proxy detected: {var}={os.environ[var]}")
                proxy_found = True
        if not proxy_found:
            print("   ✅ No proxy environment variables detected")

        # Filesystem Constraints
        print("\n💾 FILESYSTEM CONSTRAINTS")

        # Check if we can write to temp
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                tmp.write(b"test")
            print("   ✅ /tmp is writable")
        except Exception:
            print("   ❌ /tmp is NOT writable")

        # Check disk space
        try:
            stat = os.statvfs("/")
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
            used_pct = ((total_gb - free_gb) / total_gb) * 100

            if free_gb < 1:
                print(
                    f"   🔴 Disk space: {free_gb:.2f} GB free / {total_gb:.2f} GB total ({used_pct:.1f}% used) - CRITICAL"
                )
            elif free_gb < 5:
                print(
                    f"   ⚠️  Disk space: {free_gb:.2f} GB free / {total_gb:.2f} GB total ({used_pct:.1f}% used) - LOW"
                )
            else:
                print(
                    f"   ✅ Disk space: {free_gb:.2f} GB free / {total_gb:.2f} GB total ({used_pct:.1f}% used)"
                )
        except Exception:
            print("   ⚠️  Could not determine disk space")

        # Shell Information
        print("\n🐚 SHELL ENVIRONMENT")
        shell = os.environ.get("SHELL", "unknown")
        print(f"   Shell:        {shell}")
        print(f"   PATH:         {os.environ.get('PATH', 'N/A')[:100]}...")

        # MacGyver Recommendations
        print("\n💡 MACGYVER RECOMMENDATIONS")

        recommendations = []

        if shutil.which("curl") is None and shutil.which("wget") is None:
            recommendations.append(
                "   🔴 CRITICAL: No HTTP client (curl/wget). Use Python urllib or /dev/tcp"
            )

        if shutil.which("jq") is None:
            recommendations.append(
                "   🟡 WARNING: No jq. Use 'python3 -m json.tool' for JSON parsing"
            )

        if shutil.which("git") is None:
            recommendations.append(
                "   🟡 WARNING: No git. Manual file transfer required"
            )

        if is_root:
            recommendations.append(
                "   ⚠️  NOTICE: Running as root - be extra careful with destructive ops"
            )

        if not recommendations:
            print("   ✅ All critical tools available")
        else:
            for rec in recommendations:
                print(rec)

        print("\n" + "=" * 70)
        print("📋 SCAN COMPLETE")
        print("=" * 70)
        print()

        logger.info("System scan complete")

    except Exception as e:
        logger.error(f"Scan failed: {e}")
        import traceback

        traceback.print_exc()
        finalize(success=False)

    finalize(success=True)


if __name__ == "__main__":
    main()
