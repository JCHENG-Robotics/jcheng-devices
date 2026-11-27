"""Static boundary check: the device library must not touch hardware or motion.

The scan covers Python, YAML, shell, TOML and JSON files outside tests,
documentation, evidence and CI. Documentation may name forbidden devices when
explaining the boundary; code and data may not use them.

The registry describes devices declaratively. Any device-opening call, vendor
driver import, runtime-graph import or motion command in this repository is a
boundary violation.
"""

from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    ".git",
    "tests",
    "docs",
    "evidence",
    ".github",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "build",
    "install",
    "log",
}
TEXT_SUFFIXES = {
    ".py",
    ".yaml",
    ".yml",
    ".sh",
    ".toml",
    ".json",
    ".txt",
}
FORBIDDEN = (
    # Device nodes and driver libraries.
    "/dev/",
    "serial.Serial",
    "pyserial",
    "socketcan",
    "can0",
    "pigpio",
    "RPi.GPIO",
    "gpiod",
    "cv2.VideoCapture",
    "picamera",
    "/ros_robot_controller",
    "set_motor_speeds",
    "MotorsSpeedControl",
    "controller/mecanum",
    # Motion commands and runtime-graph entry points.
    "ExecuteMotion",
    "execute_motion",
    "/move_action",
    "/cmd_vel",
    "rclpy",
    "ament_",
    "ros2 run",
    "ros2 launch",
    "DDS",
)
FORBIDDEN_IMPORTS = {
    "subprocess",
    "socket",
    "serial",
    "rclpy",
    "rclpy.node",
    "rospy",
    "can",
    "gpiozero",
    "smbus",
    "evdev",
    "usb",
}
ARTIFACT_SUFFIXES = {
    ".pt",
    ".onnx",
    ".engine",
    ".bag",
    ".mcap",
    ".db3",
    ".mp4",
    ".avi",
    ".stl",
    ".dae",
    ".glb",
}


def _scanned_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        parts = path.relative_to(ROOT).parts[:-1]
        if any(part in EXCLUDED_DIRS for part in parts):
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        yield path


def test_no_device_or_motion_tokens():
    problems = []
    for path in _scanned_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in FORBIDDEN:
            if token in text:
                problems.append(f"{path.relative_to(ROOT)}: {token}")
    assert not problems, "forbidden hardware/motion tokens found:\n" + "\n".join(
        problems
    )


def test_source_imports_stay_offline():
    problems = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                root_module = name.split(".")[0]
                if root_module in FORBIDDEN_IMPORTS or name in FORBIDDEN_IMPORTS:
                    problems.append(f"{path.relative_to(ROOT)}: import {name}")
    assert not problems, "forbidden imports found:\n" + "\n".join(problems)


def test_no_weights_or_recordings():
    found = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.relative_to(ROOT).parts:
            continue
        if path.suffix in ARTIFACT_SUFFIXES:
            found.append(str(path.relative_to(ROOT)))
    assert not found, "weights, recordings or binary meshes found:\n" + "\n".join(found)


def test_gitignore_covers_artifacts():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in ("*.bag", "*.mcap", "*.pt", "*.onnx", "*.engine", "*.stl"):
        assert pattern in ignored, f".gitignore missing {pattern}"
