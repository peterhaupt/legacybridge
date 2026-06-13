"""Backend for JSON-emitting mlx-vlm models (Qwen3-VL, Gemma, ...).

The model is prompted to reply with a single JSON action object. Coordinates are
converted to LOGICAL screen pixels according to `model.coord_space` in config
(different model families report coordinates in different spaces):

  - "logical"    : already in logical screen points (what Gemma 4 emits) -> as-is
  - "image"      : absolute pixels of the input screenshot -> scale to logical
  - "normalized" : 0..1000 over the image -> scale to logical

The right value is found empirically with `--once` + a crop check.
"""

import json
import re

from mlx_vlm import generate
from mlx_vlm import load as mlx_load
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config
from PIL import Image


def load(settings):
    path = settings["model"]["path"]
    model, processor = mlx_load(path)
    return {"model": model, "processor": processor, "mlx_config": load_config(path)}


def predict(handle, task, history, image_path, screen, settings):
    # Plain .replace, not .format: the prompt embeds a literal JSON example whose
    # braces would otherwise be parsed as format fields.
    prompt = (
        settings["system_prompt"]
        .replace("{task}", task)
        .replace("{history}", "\n".join(history) if history else "(none yet)")
    )
    formatted = apply_chat_template(handle["processor"], handle["mlx_config"], prompt, num_images=1)
    result = generate(
        handle["model"],
        handle["processor"],
        formatted,
        [image_path],
        max_tokens=settings["model"]["max_tokens"],
        temperature=settings["model"]["temperature"],
        verbose=False,
    )
    # mlx-vlm returns a result object (newer) or a plain string (older).
    raw = result if isinstance(result, str) else getattr(result, "text", str(result))

    action = _parse(raw)
    _normalize_point(action)
    _to_logical(action, image_path, screen, settings["model"].get("coord_space", "logical"))
    action["raw"] = raw
    return action


def _parse(raw):
    """Pull the first JSON object out of the model's reply."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object in model reply:\n{raw}")
    return json.loads(match.group(0))


def _normalize_point(action):
    """Qwen is inconsistent about coordinate formatting: ints, floats, strings
    ("101"), or a packed array (x:[x,y]). Normalize to plain int x and y."""
    x = action.get("x")
    if isinstance(x, (list, tuple)) and len(x) >= 2:
        x, action["y"] = x[0], x[1]
        action["x"] = x
    if "x" in action:
        action["x"] = _to_int(action["x"])
    if "y" in action:
        action["y"] = _to_int(action["y"])


def _to_int(v):
    if isinstance(v, (int, float)):
        return int(v)
    m = re.search(r"-?\d+", str(v))
    if not m:
        raise ValueError(f"No integer in coordinate value: {v!r}")
    return int(m.group(0))


def _to_logical(action, image_path, screen, space):
    if "x" not in action or "y" not in action:
        return
    if space == "logical":
        return
    logical_w, logical_h = screen
    if space == "image":
        img_w, img_h = Image.open(image_path).size
        action["x"] = round(action["x"] / img_w * logical_w)
        action["y"] = round(action["y"] / img_h * logical_h)
    elif space == "normalized":
        action["x"] = round(action["x"] / 1000 * logical_w)
        action["y"] = round(action["y"] / 1000 * logical_h)
    else:
        raise ValueError(f"Unknown coord_space: {space}")
