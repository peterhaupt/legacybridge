"""Local GUI agent: screenshot -> VLM backend -> pyautogui action -> repeat.

Fully on-device. No screen data leaves the machine. The model is pluggable: pick a
backend in config (`backend: qwen`); each backend lives in backends/<name>.py and
returns a canonical action dict in LOGICAL screen coordinates.

Usage:
    python agent.py "open the customer list and create a new customer named ACME"
    python agent.py "..." --once     # dry run: one screenshot -> coords, no clicking
"""

import argparse
import importlib
import json
import os
import subprocess
import sys
import time

import pyautogui
import yaml
from PIL import ImageDraw, ImageFont

pyautogui.FAILSAFE = True  # slam the mouse into a corner to abort


def load_settings(path):
    with open(path) as f:
        return yaml.safe_load(f)


def load_backend(settings):
    """Import the model backend named in config (backends/<name>.py)."""
    return importlib.import_module(f"backends.{settings['backend']}")


def _load_font(size):
    """A legible TrueType font, falling back to PIL's bitmap default."""
    for path in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_grid(img, scale, spacing, font_size):
    """Overlay a labeled coordinate grid. Labels are in LOGICAL coords (the model's
    output space); lines are drawn in image pixels (= logical * scale). This gives
    the model fixed anchors so it can read off precise click coordinates."""
    draw = ImageDraw.Draw(img)
    font = _load_font(font_size)
    w, h = img.size
    red = (255, 0, 0)
    logical_w, logical_h = int(w / scale), int(h / scale)

    for lx in range(0, logical_w + 1, spacing):
        px = int(lx * scale)
        draw.line([(px, 0), (px, h)], fill=red, width=1)
        draw.text((px + 3, 1), str(lx), fill=red, font=font)
    for ly in range(0, logical_h + 1, spacing):
        py = int(ly * scale)
        draw.line([(0, py), (w, py)], fill=red, width=1)
        draw.text((3, py + 1), str(ly), fill=red, font=font)
    return img


def grab_screenshot(out_path, grid=None):
    """Save a screenshot and return (path, scale, width, height) where scale maps
    screenshot pixels -> logical points (Retina screens report 2x pixels vs click
    coords). If grid is enabled, a labeled coordinate grid is drawn on first."""
    shot = pyautogui.screenshot()
    logical_w, _ = pyautogui.size()
    scale = shot.width / logical_w
    if grid and grid.get("enabled"):
        draw_grid(shot, scale, grid.get("spacing", 100), grid.get("font_size", 40))
    shot.save(out_path)
    return out_path, scale, shot.width, shot.height


def write_trace(log_path, text):
    """Append a chunk to the per-run debug trace."""
    with open(log_path, "a") as f:
        f.write(text)


def bring_to_front(app_name):
    """Activate the target macOS app so we never depend on manual window focus."""
    subprocess.run(["osascript", "-e", f'tell application "{app_name}" to activate'], check=True)


def execute(action):
    """Perform the action with pyautogui. Returns a human-readable description of
    the concrete call made for the debug trace.

    Backends return coordinates already in LOGICAL screen space (= pyautogui.size()),
    which is exactly pyautogui's click space — so we click them directly, no scaling.
    """
    kind = action["action"]

    if kind in ("click", "double_click", "right_click"):
        x, y = action["x"], action["y"]
        if kind == "click":
            pyautogui.click(x, y)
        elif kind == "double_click":
            pyautogui.doubleClick(x, y)
        else:
            pyautogui.rightClick(x, y)
        return f"{kind} click_pt=({x},{y}) [logical]"
    elif kind == "type":
        pyautogui.typewrite(action["text"], interval=0.02)
        return f"type text={action['text']!r}"
    elif kind == "hotkey":
        pyautogui.hotkey(*action["keys"])
        return f"hotkey keys={action['keys']}"
    elif kind == "scroll":
        pyautogui.scroll(action["amount"])
        return f"scroll amount={action['amount']}"
    elif kind == "wait":
        return "wait (no-op)"
    else:
        raise ValueError(f"Unknown action: {kind}")


def focus_target(settings):
    """Bring the configured app to the front and wait for it to settle."""
    app = settings.get("target_app")
    if app:
        print(f"Bringing '{app}' to front ...", file=sys.stderr)
        bring_to_front(app)
        time.sleep(settings.get("focus_delay", 1.0))


def run_once(backend, handle, settings, task):
    """Dry run: one screenshot -> backend -> coordinates, execute NOTHING.
    Writes everything (raw reply, parsed action, coords, timing) to a JSON file
    so we can validate coordinates before trusting any click."""
    focus_target(settings)

    shot_path = os.path.join(settings["screenshots"]["dir"], "once.png")
    shot_path, scale, shot_w, shot_h = grab_screenshot(shot_path, settings.get("grid"))
    screen = pyautogui.size()

    t0 = time.time()
    action = backend.predict(handle, task, [], shot_path, screen, settings)
    elapsed = time.time() - t0

    result = {
        "task": task,
        "backend": settings["backend"],
        "screenshot": shot_path,
        "screenshot_size_px": [shot_w, shot_h],
        "scale": scale,
        "inference_seconds": round(elapsed, 2),
        "raw_output": action.get("raw", ""),
        "parsed_action": {k: v for k, v in action.items() if k != "raw"},
    }
    if "x" in action and "y" in action:
        result["coords"] = {"click_pt": [action["x"], action["y"]]}  # logical coords

    out_path = os.path.join(settings["screenshots"]["dir"], "once_result.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    print(f"\nNo action executed. Result written to {out_path}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task", help="what the agent should accomplish")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--once", action="store_true",
                    help="dry run: one screenshot -> coords, execute nothing")
    args = ap.parse_args()

    settings = load_settings(args.config)
    os.makedirs(settings["screenshots"]["dir"], exist_ok=True)

    backend = load_backend(settings)
    print(f"Loading backend '{settings['backend']}': {settings['model']['path']} ...", file=sys.stderr)
    handle = backend.load(settings)

    if args.once:
        run_once(backend, handle, settings, args.task)
        return

    focus_target(settings)

    start_delay = settings["loop"].get("start_delay", 0)
    if start_delay:
        print(f"Starting in {start_delay}s ...", file=sys.stderr)
        time.sleep(start_delay)

    # One scannable debug trace per run: input image, full raw reply, parsed
    # action, and the concrete pyautogui call — every step.
    log_path = os.path.join(settings["screenshots"]["dir"], "trace.log")
    with open(log_path, "w") as f:  # fresh trace per run
        f.write(f"TASK: {args.task}\nBACKEND: {settings['backend']}\n")

    screen = pyautogui.size()
    history = []
    for step in range(1, settings["loop"]["max_steps"] + 1):
        shot_path = os.path.join(settings["screenshots"]["dir"], f"step_{step:02d}.png")
        shot_path, scale, shot_w, shot_h = grab_screenshot(shot_path, settings.get("grid"))

        t0 = time.time()
        action = backend.predict(handle, args.task, history, shot_path, screen, settings)
        elapsed = time.time() - t0

        parsed = {k: v for k, v in action.items() if k != "raw"}
        write_trace(log_path, "".join([
            f"\n===== STEP {step} =====\n",
            f"[INPUT IMAGE]  {shot_path}  size={shot_w}x{shot_h}px  scale={scale}\n",
            f"[RAW OUTPUT]  ({elapsed:.1f}s)\n{action.get('raw', '')}\n",
            f"[PARSED ACTION]  {parsed}\n",
        ]))

        line = f"{step}. {action['action']} {action.get('thought', '')}".strip()
        print(line)
        history.append(line)

        if action["action"] == "done":
            write_trace(log_path, f"[EXECUTION]  done -> {action.get('reason', '')}\n")
            print(f"DONE: {action.get('reason', '')}")
            return

        detail = execute(action)
        write_trace(log_path, f"[EXECUTION]  {detail}\n")

        time.sleep(settings["loop"]["delay_after_action"])

    print("Reached max_steps without finishing.", file=sys.stderr)


if __name__ == "__main__":
    main()
