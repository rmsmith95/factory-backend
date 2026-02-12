import json
import random
import re


# --- Simulated machine state ---
_sim_state = {
    "connected": False,
    "position": {"x": 0.0, "y": 0.0, "z": 0.0, "a": 0.0},
    "mode": "G90",  # absolute mode
    "last_command": "",
}

def sim(command: str):
    """
    Simulate TinyG command execution when no hardware is connected.
    This is used when connection is None or closed.
    """
    global _sim_state
    command = command.strip()
    _sim_state["last_command"] = command

    # print(command)

    # Simulate basic responses
    response_lines = []

    # --- G-code interpretation ---
    if command.startswith("G90"):
        _sim_state["mode"] = "G90"
        response_lines.append('{"stat":3,"msg":"absolute mode"}')

    elif command.startswith("G91"):
        _sim_state["mode"] = "G91"
        response_lines.append('{"stat":3,"msg":"relative mode"}')

    elif command.startswith("G92"):
        # Example: G92 X0 Y0 Z0 A0
        match = re.findall(r"([XYZAB])([-+]?[0-9]*\.?[0-9]+)", command)
        for axis, val in match:
            _sim_state["position"][axis.lower()] = float(val)
        response_lines.append(json.dumps({
            "msg": "position set", "pos": _sim_state["position"]
        }))

    elif command.startswith("G1") or command.startswith("G0"):
        # Example: G1 X10 Y20 Z5 F1000
        match = re.findall(r"([XYZAB])([-+]?[0-9]*\.?[0-9]+)", command)
        for axis, val in match:
            if _sim_state["mode"] == "G90":
                _sim_state["position"][axis.lower()] = float(val)
            else:
                _sim_state["position"][axis.lower()] += float(val)

        response_lines.append(json.dumps({
            "msg": "simulated move complete",
            "pos": _sim_state["position"]
        }))

    elif command == "$H":
        # Home all axes
        _sim_state["position"] = {"x": 0, "y": 0, "z": 0, "a": 0}
        response_lines.append('{"msg":"homed all axes"}')

    elif command == "!":
        response_lines.append('{"msg":"feed hold (paused)"}')

    elif command == "~":
        response_lines.append('{"msg":"cycle start (resumed)"}')

    elif command == "?":
        # Status query
        pos = _sim_state["position"]
        response_lines = [
            {"raw": f"X position: {pos['x']}"},
            {"raw": f"Y position: {pos['y']}"},
            {"raw": f"Z position: {pos['z']}"},
            {"raw": f"A position: {pos['a']}"}
        ]

    else:
        # Unknown command fallback
        response_lines.append(json.dumps({
            "msg": f"simulated ok for '{command}'"
        }))

    # Add a small fake delay
    # time.sleep(random.uniform(0.01, 0.05))

    return {
        "connection": "simulated",
        "status": response_lines,
    }
