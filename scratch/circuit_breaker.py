#!/usr/bin/env python3
"""
Circuit Breaker Library: Runaway Loop Protection

Implements circuit breaker pattern for detecting and blocking
runaway loops in tools, hooks, and agents.
"""

import sys
import json
import fcntl
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='[%(name)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('circuit_breaker')

# Paths
MEMORY_DIR = Path(__file__).resolve().parent.parent / ".claude" / "memory"
CIRCUIT_STATE_FILE = MEMORY_DIR / "circuit_breaker_state.json"
CIRCUIT_INCIDENTS_FILE = MEMORY_DIR / "circuit_breaker_incidents.jsonl"
CIRCUIT_CONFIG_FILE = MEMORY_DIR / "circuit_breaker_config.json"

# Configurable constants
ERROR_MESSAGE_MAX_LENGTH = 100
METADATA_MAX_LENGTH = 200
SUCCESS_RECOVERY_THRESHOLD = 5
EXPONENTIAL_BACKOFF_MULTIPLIERS = [1, 2, 6, 12, 60]
BYPASS_KEYWORD = "SUDO BYPASS"

# Default configuration
DEFAULT_CONFIG = {
    "circuit_breakers": {
        "hook_recursion": {
            "enabled": True,
            "threshold": 5,
            "window_turns": 10,
            "cooldown_base_seconds": 5,
        },
        "tool_failure": {
            "enabled": True,
            "threshold": 3,
            "window_turns": 5,
            "cooldown_base_seconds": 10,
        },
        "sequential_tools": {
            "enabled": True,
            "threshold": 10,
            "window_turns": 1,
            "cooldown_base_seconds": 5,
        },
        "agent_spawn": {
            "enabled": True,
            "threshold": 5,
            "window_turns": 10,
            "cooldown_base_seconds": 10,
        },
        "external_api": {
            "enabled": True,
            "threshold": 10,
            "window_seconds": 60,
            "session_max": 50,
            "cooldown_base_seconds": 30,
        },
    },
    "memory_limits": {
        "telemetry_max_lines": 1000,
        "telemetry_max_kb": 50,
        "telemetry_max_age_days": 7,
        "telemetry_keep_rotations": 5,
        "session_max_active": 10,
        "session_max_age_days": 7,
        "evidence_ledger_max": 100,
        "tool_history_max": 50,
    },
    "resource_limits": {
        "max_concurrent_agents": 5,
        "max_agents_per_session": 10,
        "agent_spawn_cooldown_seconds": 10,
        "api_rate_limit_per_minute": 10,
        "api_session_max": 50,
        "api_cost_warn_usd": 1.0,
        "api_cost_block_usd": 5.0,
    },
}

# Circuit breaker states
STATE_CLOSED = "CLOSED"  # Normal operation
STATE_OPEN = "OPEN"  # Blocked, cooldown active
STATE_HALF_OPEN = "HALF_OPEN"  # Cooldown expired, probing


def load_config() -> Dict:
    """Load circuit breaker configuration"""
    if not CIRCUIT_CONFIG_FILE.exists():
        CIRCUIT_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CIRCUIT_CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CIRCUIT_CONFIG_FILE) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Config file corrupted: {e}. Using defaults.")
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        logger.warning(f"Failed to load config: {e}. Using defaults.")
        return DEFAULT_CONFIG.copy()


def load_circuit_state() -> Dict:
    """Load current circuit breaker state"""
    if not CIRCUIT_STATE_FILE.exists():
        state = {
            "circuits": {},
            "initialized_at": datetime.now().isoformat(),
        }
        CIRCUIT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CIRCUIT_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        return state

    try:
        with open(CIRCUIT_STATE_FILE) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Circuit state corrupted: {e}. Resetting to defaults.")
        return {
            "circuits": {},
            "initialized_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.warning(f"Failed to load circuit state: {e}. Using defaults.")
        return {
            "circuits": {},
            "initialized_at": datetime.now().isoformat(),
        }



def save_circuit_state_safe(state: Dict) -> bool:
    """
    Save circuit breaker state with file locking and error handling

    Returns:
        True if save succeeded, False otherwise
    """
    try:
        CIRCUIT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Open with exclusive lock
        with open(CIRCUIT_STATE_FILE, 'w') as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(state, f, indent=2)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return True
            except Exception as e:
                logger.error(f"Failed to save circuit state: {e}")
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return False
    except Exception as e:
        logger.error(f"Failed to open circuit state file: {e}")
        return False


def save_circuit_state(state: Dict) -> None:
    """Legacy wrapper for backward compatibility"""
    save_circuit_state_safe(state)



def log_incident(
    circuit_name: str, reason: str, turn: int, metadata: Dict = None
) -> None:
    """Log circuit breaker incident to JSONL"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "circuit": circuit_name,
        "reason": reason,
        "turn": turn,
        "metadata": metadata or {},
    }

    try:
        CIRCUIT_INCIDENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CIRCUIT_INCIDENTS_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to log incident: {e}")


def initialize_circuit(circuit_name: str, config: Dict) -> Dict:
    """Initialize circuit breaker for a pattern"""
    breaker_config = config["circuit_breakers"].get(circuit_name, {})

    return {
        "state": STATE_CLOSED,
        "failure_count": 0,
        "last_failure_time": None,
        "trip_count": 0,
        "last_trip_time": None,
        "cooldown_expires_at": None,
        "exponential_backoff_level": 0,
        "window": [],  # Sliding window of events
        "config": breaker_config,
    }


def add_event_to_window(
    circuit: Dict, turn: int, event_type: str, metadata: Dict = None
) -> None:
    """
    Add event to circuit's sliding window

    Args:
        circuit: Circuit breaker state dict
        turn: Current turn number
        event_type: Type of event (failure, success, etc)
        metadata: Additional event data
    """
    event = {
        "turn": turn,
        "timestamp": time.time(),
        "type": event_type,
        "metadata": metadata or {},
    }

    circuit["window"].append(event)

    # Trim window based on config
    config = circuit["config"]
    if "window_turns" in config:
        # Turn-based window
        window_size = config["window_turns"]
        circuit["window"] = [e for e in circuit["window"] if (turn - e["turn"]) <= window_size]
    elif "window_seconds" in config:
        # Time-based window
        window_size = config["window_seconds"]
        now = time.time()
        circuit["window"] = [
            e for e in circuit["window"] if (now - e["timestamp"]) <= window_size
        ]


def count_events_in_window(
    circuit: Dict, event_types: Optional[List[str]] = None
) -> int:
    """
    Count events in current window

    Args:
        circuit: Circuit breaker state dict
        event_types: Filter by event types (None = count all)

    Returns:
        Number of matching events in window
    """
    if event_types is None:
        return len(circuit["window"])

    return sum(1 for e in circuit["window"] if e["type"] in event_types)


def check_threshold_exceeded(circuit: Dict) -> bool:
    """Check if circuit threshold exceeded"""
    config = circuit["config"]
    threshold = config.get("threshold", 5)
    failure_count = count_events_in_window(circuit, ["failure"])

    return failure_count >= threshold


def calculate_cooldown(circuit: Dict) -> float:
    """
    Calculate cooldown duration using exponential backoff

    Returns:
        Cooldown duration in seconds
    """
    config = circuit["config"]
    base_cooldown = config.get("cooldown_base_seconds", 5)
    backoff_level = circuit["exponential_backoff_level"]

    # Exponential backoff: 5s, 10s, 30s, 60s, 300s
    backoff_multipliers = EXPONENTIAL_BACKOFF_MULTIPLIERS
    multiplier = backoff_multipliers[min(backoff_level, len(backoff_multipliers) - 1)]

    return base_cooldown * multiplier


def trip_circuit(circuit: Dict, reason: str, turn: int) -> str:
    """
    Trip circuit breaker (CLOSED/HALF_OPEN → OPEN)

    Returns:
        Message explaining why circuit tripped and cooldown time
    """
    circuit["state"] = STATE_OPEN
    circuit["trip_count"] += 1
    circuit["last_trip_time"] = time.time()
    circuit["exponential_backoff_level"] += 1

    cooldown_seconds = calculate_cooldown(circuit)
    circuit["cooldown_expires_at"] = time.time() + cooldown_seconds

    # Log incident
    log_incident(
        circuit_name=circuit["config"].get("name", "unknown"),
        reason=reason,
        turn=turn,
        metadata={
            "trip_count": circuit["trip_count"],
            "backoff_level": circuit["exponential_backoff_level"],
            "cooldown_seconds": cooldown_seconds,
        },
    )

    return f"""🚨 CIRCUIT BREAKER TRIPPED

Reason: {reason}
Trip Count: {circuit['trip_count']}
Cooldown: {cooldown_seconds:.0f}s (backoff level {circuit['exponential_backoff_level']})

Exponential backoff active. Each repeated failure increases cooldown.
Next attempt allowed at: {datetime.fromtimestamp(circuit['cooldown_expires_at']).strftime('%H:%M:%S')}

Bypass: Include "SUDO BYPASS" keyword in prompt to override
"""


def check_circuit_state(
    circuit_name: str, session_id: str, turn: int
) -> Tuple[str, Optional[str]]:
    """
    Check if circuit breaker allows operation

    Args:
        circuit_name: Name of circuit to check
        session_id: Current session ID
        turn: Current turn number

    Returns:
        Tuple[str, Optional[str]]: (state, message)
        - state: "allow" | "block" | "probe"
        - message: Block/warning message (None if allow)
    """
    config = load_config()
    state = load_circuit_state()

    # Initialize circuit if not exists
    if circuit_name not in state["circuits"]:
        state["circuits"][circuit_name] = initialize_circuit(circuit_name, config)

    circuit = state["circuits"][circuit_name]

    # Check if circuit disabled in config
    if not circuit["config"].get("enabled", True):
        return ("allow", None)

    # STATE: CLOSED - Normal operation
    if circuit["state"] == STATE_CLOSED:
        return ("allow", None)

    # STATE: OPEN - Cooldown active
    elif circuit["state"] == STATE_OPEN:
        now = time.time()
        cooldown_expires = circuit["cooldown_expires_at"]

        if now < cooldown_expires:
            # Still in cooldown
            remaining = cooldown_expires - now
            message = f"""🚫 CIRCUIT BREAKER: {circuit_name.upper()} BLOCKED

State: OPEN (cooldown active)
Remaining: {remaining:.0f}s
Trip Count: {circuit['trip_count']}
Last Trip: Turn {turn - 1}

Cooldown active due to repeated failures. Wait for cooldown to expire.

Bypass: Include "SUDO BYPASS" keyword to override
"""
            return ("block", message)
        else:
            # Cooldown expired, transition to HALF_OPEN
            circuit["state"] = STATE_HALF_OPEN
            save_circuit_state(state)
            message = f"""⚠️ CIRCUIT BREAKER: {circuit_name.upper()} PROBING

State: HALF_OPEN (cooldown expired, testing)
Next action will determine if circuit closes or trips again.

If this action succeeds, circuit will close (normal operation).
If this action fails, circuit will trip again with longer cooldown.
"""
            return ("probe", message)

    # STATE: HALF_OPEN - Probing after cooldown
    elif circuit["state"] == STATE_HALF_OPEN:
        message = f"""⚠️ CIRCUIT BREAKER: {circuit_name.upper()} PROBING

State: HALF_OPEN (testing after cooldown)
This is a probe attempt - proceed carefully.

Success → Circuit closes (normal operation)
Failure → Circuit trips again (longer cooldown)
"""
        return ("probe", message)

    return ("allow", None)


def record_success(circuit_name: str, session_id: str, turn: int) -> Optional[str]:
    """
    Record successful operation

    Returns:
        Message if circuit state changed (None otherwise)
    """
    state = load_circuit_state()
    config = load_config()

    if circuit_name not in state["circuits"]:
        state["circuits"][circuit_name] = initialize_circuit(circuit_name, config)

    circuit = state["circuits"][circuit_name]

    # Add success event to window
    add_event_to_window(circuit, turn, "success")

    # STATE: HALF_OPEN → CLOSED on success
    if circuit["state"] == STATE_HALF_OPEN:
        circuit["state"] = STATE_CLOSED
        circuit["exponential_backoff_level"] = max(
            0, circuit["exponential_backoff_level"] - 1
        )  # Decay backoff
        save_circuit_state(state)

        return f"""✅ CIRCUIT BREAKER: {circuit_name.upper()} CLOSED

State: HALF_OPEN → CLOSED (probe succeeded)
Circuit now operating normally.
Backoff level reduced to {circuit['exponential_backoff_level']}.
"""

    # STATE: CLOSED - reset backoff gradually on sustained success
    elif circuit["state"] == STATE_CLOSED:
        success_count = count_events_in_window(circuit, ["success"])
        if (
            success_count >= SUCCESS_RECOVERY_THRESHOLD and circuit["exponential_backoff_level"] > 0
        ):  # Consecutive successes trigger backoff decay
            circuit["exponential_backoff_level"] = max(
                0, circuit["exponential_backoff_level"] - 1
            )
            save_circuit_state(state)

    save_circuit_state(state)
    return None


def record_failure(
    circuit_name: str, session_id: str, turn: int, reason: str, metadata: Dict = None
) -> Optional[str]:
    """
    Record failed operation

    Returns:
        Message if circuit tripped (None otherwise)
    """
    state = load_circuit_state()
    config = load_config()

    if circuit_name not in state["circuits"]:
        state["circuits"][circuit_name] = initialize_circuit(circuit_name, config)

    circuit = state["circuits"][circuit_name]

    # Add failure event to window
    add_event_to_window(circuit, turn, "failure", metadata)

    # Check if threshold exceeded
    if check_threshold_exceeded(circuit):
        # Trip circuit
        message = trip_circuit(circuit, reason, turn)
        save_circuit_state(state)
        return message

    # STATE: HALF_OPEN → OPEN on failure
    elif circuit["state"] == STATE_HALF_OPEN:
        message = trip_circuit(
            circuit, f"Probe failed: {reason}", turn
        )
        save_circuit_state(state)
        return message

    save_circuit_state(state)
    return None


def get_circuit_status(circuit_name: Optional[str] = None) -> str:
    """
    Get circuit breaker status report

    Args:
        circuit_name: Specific circuit (None = all circuits)

    Returns:
        Status report string
    """
    state = load_circuit_state()
    config = load_config()

    if not state["circuits"]:
        return "🔒 CIRCUIT BREAKER STATUS\n\nNo circuits initialized yet (all systems operational)."

    output = ["🔒 CIRCUIT BREAKER STATUS\n"]

    # Filter circuits
    circuits_to_show = (
        {circuit_name: state["circuits"][circuit_name]}
        if circuit_name and circuit_name in state["circuits"]
        else state["circuits"]
    )

    # Show active breakers (OPEN or HALF_OPEN)
    active = [
        (name, c) for name, c in circuits_to_show.items() if c["state"] != STATE_CLOSED
    ]

    if active:
        output.append("Active Breakers:")
        for name, circuit in active:
            output.append(f"  • {name}: {circuit['state']}")

            if circuit["state"] == STATE_OPEN:
                remaining = circuit["cooldown_expires_at"] - time.time()
                output.append(f"    - Cooldown: {remaining:.0f}s remaining")
                output.append(
                    f"    - Last trip: {circuit.get('last_trip_time', 'unknown')}"
                )
                output.append(f"    - Trip count: {circuit['trip_count']}")

            elif circuit["state"] == STATE_HALF_OPEN:
                output.append("    - Probing (next action determines state)")

        output.append("")
    else:
        output.append("Active Breakers: None (all systems operational)\n")

    # Show all circuits summary
    output.append("All Circuits:")
    for name, circuit in circuits_to_show.items():
        state_icon = {
            STATE_CLOSED: "✅",
            STATE_OPEN: "🚫",
            STATE_HALF_OPEN: "⚠️",
        }
        icon = state_icon.get(circuit["state"], "❓")
        output.append(
            f"  {icon} {name}: {circuit['state']} (trips: {circuit['trip_count']}, backoff: {circuit['exponential_backoff_level']})"
        )

    return "\n".join(output)


def reset_circuit(circuit_name: str) -> str:
    """
    Manually reset circuit breaker (admin override)

    Returns:
        Confirmation message
    """
    state = load_circuit_state()

    if circuit_name not in state["circuits"]:
        return f"❌ Circuit '{circuit_name}' not found"

    circuit = state["circuits"][circuit_name]
    old_state = circuit["state"]

    # Reset to CLOSED
    circuit["state"] = STATE_CLOSED
    circuit["failure_count"] = 0
    circuit["exponential_backoff_level"] = 0
    circuit["window"] = []

    save_circuit_state(state)

    return f"""✅ CIRCUIT BREAKER RESET

Circuit: {circuit_name}
Old State: {old_state} → CLOSED
Backoff level reset to 0
Window cleared

Manual override applied. Circuit now operating normally.
"""


def reset_all_circuits() -> str:
    """Reset all circuit breakers"""
    state = load_circuit_state()

    reset_count = 0
    for circuit_name in state["circuits"].keys():
        circuit = state["circuits"][circuit_name]
        if circuit["state"] != STATE_CLOSED:
            circuit["state"] = STATE_CLOSED
            circuit["failure_count"] = 0
            circuit["exponential_backoff_level"] = 0
            circuit["window"] = []
            reset_count += 1

    save_circuit_state(state)

    return f"""✅ ALL CIRCUIT BREAKERS RESET

Circuits reset: {reset_count}
All circuits now CLOSED (normal operation)

Manual override applied.
"""
