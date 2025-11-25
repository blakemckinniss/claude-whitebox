#!/usr/bin/env python3
"""
System Stats Hook: Reports system performance, open ports, and running services at session start.
Triggers on: SessionStart

Output includes:
- CPU/Memory/Disk usage
- Platform details (WSL2 detection)
- Open ports (listening services)
- Key running processes
"""
import subprocess
import sys
import os
import glob as globlib
from pathlib import Path

def get_cpu_info():
    """Get CPU usage and load average."""
    try:
        # Load average (1, 5, 15 min)
        load = os.getloadavg()

        # CPU count
        cpu_count = os.cpu_count() or 1

        # Normalize load to percentage
        load_pct = (load[0] / cpu_count) * 100

        return {
            "load_1m": f"{load[0]:.2f}",
            "load_5m": f"{load[1]:.2f}",
            "load_15m": f"{load[2]:.2f}",
            "cores": cpu_count,
            "load_pct": f"{load_pct:.0f}%"
        }
    except Exception:
        return {"error": "unavailable"}

def get_memory_info():
    """Get memory usage from /proc/meminfo."""
    try:
        with open("/proc/meminfo") as f:
            meminfo = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    value = int(parts[1])  # in kB
                    meminfo[key] = value

        total = meminfo.get("MemTotal", 0)
        available = meminfo.get("MemAvailable", 0)
        used = total - available
        used_pct = (used / total * 100) if total > 0 else 0

        return {
            "total_gb": f"{total / 1024 / 1024:.1f}GB",
            "used_gb": f"{used / 1024 / 1024:.1f}GB",
            "available_gb": f"{available / 1024 / 1024:.1f}GB",
            "used_pct": f"{used_pct:.0f}%"
        }
    except Exception:
        return {"error": "unavailable"}

def get_disk_info():
    """Get disk usage for key paths."""
    try:
        import shutil
        results = {}
        for path, name in [("/", "root"), (str(Path.home()), "home")]:
            if Path(path).exists():
                usage = shutil.disk_usage(path)
                used_pct = (usage.used / usage.total) * 100
                results[name] = {
                    "total_gb": f"{usage.total / 1024**3:.0f}GB",
                    "free_gb": f"{usage.free / 1024**3:.0f}GB",
                    "used_pct": f"{used_pct:.0f}%"
                }
        return results
    except Exception:
        return {"error": "unavailable"}

def get_platform_info():
    """Detect platform and WSL2 status."""
    info = {
        "platform": sys.platform,
        "wsl2": False,
        "kernel": "unknown"
    }

    # Check for WSL2
    try:
        with open("/proc/version") as f:
            version = f.read().lower()
            info["wsl2"] = "microsoft" in version or "wsl" in version
            # Extract kernel version
            parts = version.split()
            if len(parts) >= 3:
                info["kernel"] = parts[2]
    except Exception:
        pass

    return info

def get_gpu_info():
    """Get GPU info via nvidia-smi if available."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version",
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(", ")
            if len(parts) >= 4:
                return {
                    "name": parts[0].strip(),
                    "vram_total": f"{int(parts[1].strip())}MB",
                    "vram_used": f"{int(parts[2].strip())}MB",
                    "driver": parts[3].strip()
                }
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None

def get_docker_info():
    """Get Docker status and running containers."""
    try:
        # Check if docker daemon is running
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return {"status": "daemon not running"}

        # Get running containers
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}:{{.Image}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        containers = []
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line:
                    containers.append(line)

        return {
            "status": "running",
            "containers": containers[:5]  # Top 5
        }
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}

def get_project_stack():
    """Detect project type from manifest files."""
    cwd = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    stacks = []

    markers = {
        "package.json": "Node.js",
        "Cargo.toml": "Rust",
        "pyproject.toml": "Python (modern)",
        "setup.py": "Python",
        "requirements.txt": "Python",
        "go.mod": "Go",
        "Gemfile": "Ruby",
        "pom.xml": "Java (Maven)",
        "build.gradle": "Java (Gradle)",
        "composer.json": "PHP",
        "mix.exs": "Elixir",
    }

    for marker, stack in markers.items():
        if Path(cwd, marker).exists():
            stacks.append(stack)

    # Check for monorepo patterns
    if globlib.glob(f"{cwd}/packages/*/package.json"):
        stacks.append("Monorepo")

    return stacks[:3] if stacks else ["Unknown"]

def get_python_env():
    """Get Python virtual environment status."""
    info = {
        "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "venv": None
    }

    # Check for active venv
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        info["venv"] = Path(venv).name

    # Check for conda
    conda = os.environ.get("CONDA_DEFAULT_ENV")
    if conda:
        info["venv"] = f"conda:{conda}"

    return info

def get_git_extended():
    """Get extended git info: stash, ahead/behind."""
    try:
        info = {}

        # Stash count
        result = subprocess.run(
            ["git", "stash", "list"],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0:
            stash_count = len([l for l in result.stdout.strip().split("\n") if l])
            if stash_count:
                info["stash"] = stash_count

        # Ahead/behind
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split()
            if len(parts) == 2:
                ahead, behind = int(parts[0]), int(parts[1])
                if ahead:
                    info["ahead"] = ahead
                if behind:
                    info["behind"] = behind

        return info if info else None
    except Exception:
        return None

def get_optimal_tools():
    """Detect available optimized CLI tools vs defaults."""
    tool_pairs = [
        # (optimal, fallback, category)
        ("rg", "grep", "search"),
        ("fd", "find", "find"),
        ("bat", "cat", "view"),
        ("eza", "ls", "list"),
        ("exa", "ls", "list"),  # older name for eza
        ("delta", "diff", "diff"),
        ("dust", "du", "disk"),
        ("duf", "df", "disk"),
        ("btop", "top", "monitor"),
        ("htop", "top", "monitor"),
        ("procs", "ps", "process"),
        ("zoxide", "cd", "nav"),
        ("fzf", None, "fuzzy"),
        ("jq", None, "json"),
        ("yq", None, "yaml"),
        ("hyperfine", "time", "bench"),
        ("tokei", "cloc", "stats"),
        ("glow", None, "markdown"),
        ("lazygit", "git", "git"),
        ("gh", None, "github"),
        ("uv", "pip", "python"),
        ("ruff", "flake8", "lint"),
        ("just", "make", "tasks"),
        ("watchexec", None, "watch"),
        ("entr", None, "watch"),
    ]

    available = {}
    fallbacks = {}

    for optimal, fallback, category in tool_pairs:
        # Check if optimal tool exists
        result = subprocess.run(
            ["which", optimal],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            if category not in available:
                available[category] = optimal
        elif fallback:
            # Check fallback
            result = subprocess.run(
                ["which", fallback],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                fallbacks[category] = fallback

    return {"optimal": available, "fallbacks": fallbacks}

def get_open_ports():
    """Get listening ports using ss command."""
    try:
        result = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True,
            text=True,
            timeout=5
        )

        ports = []
        for line in result.stdout.strip().split("\n")[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 4:
                # Extract port from Local Address (e.g., *:8080 or 127.0.0.1:3000)
                local_addr = parts[3]
                if ":" in local_addr:
                    port = local_addr.rsplit(":", 1)[-1]
                    # Try to get process name
                    proc = ""
                    if len(parts) >= 6:
                        proc_info = parts[-1]
                        if "users:" in proc_info:
                            # Extract process name from users:(("name",pid=...))
                            try:
                                proc = proc_info.split('"')[1]
                            except IndexError:
                                pass

                    port_entry = f"{port}"
                    if proc:
                        port_entry += f" ({proc})"
                    # Check by port number to avoid duplicates
                    port_num = port_entry.split()[0]
                    if port_num not in [p.split()[0] for p in ports]:
                        ports.append(port_entry)

        return sorted(ports, key=lambda x: int(x.split()[0]) if x.split()[0].isdigit() else 0)
    except Exception as e:
        return [f"error: {e}"]

def get_key_processes():
    """Get key running processes (dev-related)."""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Keywords for dev-related processes
        keywords = [
            "node", "npm", "python", "pip", "cargo", "rust",
            "docker", "postgres", "mysql", "redis", "mongo",
            "nginx", "apache", "code-server", "jupyter"
        ]

        processes = []
        for line in result.stdout.strip().split("\n")[1:]:  # Skip header
            line_lower = line.lower()
            for kw in keywords:
                if kw in line_lower:
                    parts = line.split()
                    if len(parts) >= 11:
                        cmd = " ".join(parts[10:])[:50]  # Truncate command
                        cpu = parts[2]
                        mem = parts[3]
                        processes.append({
                            "cmd": cmd,
                            "cpu": f"{float(cpu):.1f}%",
                            "mem": f"{float(mem):.1f}%"
                        })
                    break

        # Dedupe and limit
        seen = set()
        unique = []
        for p in processes:
            key = p["cmd"][:20]
            if key not in seen:
                seen.add(key)
                unique.append(p)

        return unique[:10]  # Top 10
    except Exception as e:
        return [{"error": str(e)}]

def format_output():
    """Format all stats for display."""
    cpu = get_cpu_info()
    mem = get_memory_info()
    disk = get_disk_info()
    platform = get_platform_info()
    ports = get_open_ports()
    procs = get_key_processes()
    gpu = get_gpu_info()
    docker = get_docker_info()
    stack = get_project_stack()
    pyenv = get_python_env()
    git_ext = get_git_extended()
    tools = get_optimal_tools()

    lines = ["🖥️  SYSTEM CONTEXT:"]

    # Platform + Stack
    wsl_badge = " (WSL2)" if platform.get("wsl2") else ""
    stack_str = ", ".join(stack)
    lines.append(f"   Platform: {platform['platform']}{wsl_badge} | Stack: {stack_str}")

    # Performance
    lines.append(f"   CPU: {cpu.get('load_pct', '?')} load ({cpu.get('cores', '?')} cores) | "
                 f"Memory: {mem.get('used_pct', '?')} of {mem.get('total_gb', '?')} | "
                 f"Disk: {disk.get('root', {}).get('free_gb', '?')} free")

    # Python env
    py_str = f"Python: {pyenv['version']}"
    if pyenv.get("venv"):
        py_str += f" ({pyenv['venv']})"
    lines.append(f"   {py_str}")

    # GPU (if available)
    if gpu:
        lines.append(f"   GPU: {gpu['name']} | VRAM: {gpu['vram_used']}/{gpu['vram_total']} | Driver: {gpu['driver']}")

    # Docker (if available)
    if docker:
        if docker.get("status") == "running":
            container_count = len(docker.get("containers", []))
            if container_count:
                container_names = ", ".join([c.split(":")[0] for c in docker["containers"][:3]])
                lines.append(f"   Docker: {container_count} containers ({container_names})")
            else:
                lines.append("   Docker: running (no containers)")
        elif docker.get("status") == "daemon not running":
            lines.append("   Docker: daemon not running")

    # Git extended
    if git_ext:
        git_parts = []
        if git_ext.get("stash"):
            git_parts.append(f"stash:{git_ext['stash']}")
        if git_ext.get("ahead"):
            git_parts.append(f"ahead:{git_ext['ahead']}")
        if git_ext.get("behind"):
            git_parts.append(f"behind:{git_ext['behind']}")
        if git_parts:
            lines.append(f"   Git: {', '.join(git_parts)}")

    # Open ports (compact)
    if ports and not any("error" in str(p) for p in ports):
        port_str = ", ".join(ports[:6])
        if len(ports) > 6:
            port_str += f" +{len(ports)-6}"
        lines.append(f"   Ports: {port_str}")

    # Key processes (only if high resource usage)
    high_usage = []
    for p in procs:
        try:
            if 'error' in p:
                continue
            cpu_val = float(p.get('cpu', '0%').rstrip('%'))
            mem_val = float(p.get('mem', '0%').rstrip('%'))
            if cpu_val > 1.0 or mem_val > 1.0:
                high_usage.append(p)
        except (ValueError, AttributeError):
            pass  # Skip malformed entries
    if high_usage:
        lines.append("   Active:")
        for p in high_usage[:3]:
            lines.append(f"     • {p['cmd'][:35]} (CPU:{p['cpu']}, MEM:{p['mem']})")

    # Optimal CLI tools available
    if tools["optimal"]:
        tool_list = [f"{tool}" for tool in sorted(tools["optimal"].values())]
        lines.append(f"   CLI: {', '.join(tool_list)}")

    return "\n".join(lines)

if __name__ == "__main__":
    print(format_output())
    sys.exit(0)
