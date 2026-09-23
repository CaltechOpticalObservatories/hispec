"""Per-model capability lookup for the PDU daemon.

Loads capability flags from pdu_models/<model>.yaml, one file per PDU
model. Kept separate from the daemon script itself (pdu).
"""
import pathlib
from typing import Dict, List

try:
    import yaml
except ImportError:
    yaml = None

# Directory of per-model capability files, next to this module. The model
# key used in a deployment's hardware.model is the filename stem, e.g.
# "eaton_emat0810" -> pdu_models/eaton_emat0810.yaml.
MODEL_CAPABILITIES_DIR = pathlib.Path(__file__).resolve().parent / "pdu_models"

# Every capability file must define these flags; see pdu_models/eaton_emat0810.yaml
# for what each one gates.
REQUIRED_CAPABILITY_FLAGS = (
    "has_outlet_amps", "has_outlet_draw", "has_outlet_pos", "has_outlet_wh",
    "has_strip_amps", "has_strip_draw", "has_hardware_ver",
)


def known_models() -> List[str]:
    """List model keys with a capability file on disk, sorted."""
    if not MODEL_CAPABILITIES_DIR.is_dir():
        return []
    return sorted(p.stem for p in MODEL_CAPABILITIES_DIR.glob("*.yaml"))


def model_capabilities(model: str) -> Dict[str, bool]:
    """Load the capability flags for a configured PDU model.

    Reads pdu_models/<model>.yaml. Raises a ValueError listing the known
    models if ``model`` isn't recognized, or naming any flags missing from
    its capability file, so a typo in config (or an incomplete capability
    file) fails loudly at startup rather than silently omitting keywords.
    """
    path = MODEL_CAPABILITIES_DIR / f"{model}.yaml"
    if not model or not path.is_file():
        raise ValueError(f"unknown PDU model '{model}'; known models: {known_models()}")
    if yaml is None:
        raise ValueError("PyYAML is required to load PDU model capability files")
    caps = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    missing = [flag for flag in REQUIRED_CAPABILITY_FLAGS if flag not in caps]
    if missing:
        raise ValueError(f"PDU model '{model}' capability file {path} is missing: {missing}")
    return {flag: bool(caps[flag]) for flag in REQUIRED_CAPABILITY_FLAGS}
