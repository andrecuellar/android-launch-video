"""Shared configuration of the toolkit.

Reads /PATH/TO/WORKDIR/config.json (setup.sh creates it from config.example.json). Any key can be
overridden with an environment variable ALV_<KEY IN UPPER CASE>, e.g. ALV_EMULATOR_SERIAL=emulator-5556
(lists and objects are given as JSON).

As a module (scripts run with `python -I`, so the work dir is added by hand):
    import sys; sys.path.insert(0, "/PATH/TO/WORKDIR")
    from kitconfig import cfg
    cfg("emulator_serial")
From a shell (lists are printed space separated):
    python3 /PATH/TO/WORKDIR/kitconfig.py emulator_serial
"""
import json
import os
import sys

WORKDIR = "/PATH/TO/WORKDIR"
CONFIG_PATH = os.path.join(WORKDIR, "config.json")


def _load():
    if not os.path.exists(CONFIG_PATH):
        raise SystemExit(f"missing {CONFIG_PATH}: copy config.example.json to config.json and edit it")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


CONFIG = _load()


def cfg(key):
    """Value of a configuration key; the env var ALV_<KEY> wins over config.json."""
    env = os.environ.get("ALV_" + key.upper())
    current = CONFIG.get(key)
    if env is not None:
        if isinstance(current, (list, dict)):
            return json.loads(env)
        if isinstance(current, (int, float)) and not isinstance(current, bool):
            return type(current)(env)
        return env
    if key not in CONFIG:
        raise SystemExit(f"missing config key '{key}' (see config.example.json)")
    return current


def windows_command(exe, *args):
    """Command list that runs a Windows .exe from WSL, through the optional wrapper."""
    wrapper = cfg("windows_exec_wrapper")
    return ([wrapper] if wrapper else []) + [exe, *args]


if __name__ == "__main__":
    value = cfg(sys.argv[1])
    print(" ".join(str(v) for v in value) if isinstance(value, list) else value)
