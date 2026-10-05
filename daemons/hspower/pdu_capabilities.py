"""Per-model description lookup for the PDU daemon.

One file per PDU model in pdu_models/<model>.yaml, the way kpdu keeps one
.def file per model. Each names its pdu_drivers adapter and sets the
capability flags that decide which keywords the daemon registers.
"""
import dataclasses
import pathlib
from typing import Dict, List

try:
    import yaml
except ImportError:
    yaml = None

# Per-model files, next to this module. A deployment's hardware.model is the
# filename stem, e.g. "eaton_emat0810" -> pdu_models/eaton_emat0810.yaml.
MODEL_DIR = pathlib.Path(__file__).resolve().parent / "pdu_models"

# Capability flags a model file may set, each naming a pdu_drivers capability
# with the "has_" prefix dropped. A flag left out defaults to false, so a new
# flag does not mean revisiting every other model's file.
CAPABILITY_FLAGS = (
    "has_outlet_amps", "has_outlet_draw", "has_outlet_pos", "has_outlet_wh",
    "has_strip_amps", "has_strip_draw", "has_hardware_ver",
    "has_manufacturer", "has_serial",
)


@dataclasses.dataclass(frozen=True)
class PduModel:
    """What pdu_models/<key>.yaml says about one PDU model."""

    key: str
    driver: str
    capabilities: Dict[str, bool]


def known_models() -> List[str]:
    """List model keys with a file on disk, sorted."""
    if not MODEL_DIR.is_dir():
        return []
    return sorted(p.stem for p in MODEL_DIR.glob("*.yaml"))


def load_model(model: str) -> PduModel:
    """Load the description of a configured PDU model.

    Reads pdu_models/<model>.yaml, raising a ValueError on an unknown model,
    a missing driver, or a key that is not a capability, so a typo in config
    or in a model file fails at startup rather than silently dropping
    keywords.
    """
    path = MODEL_DIR / f"{model}.yaml"
    if not model or not path.is_file():
        raise ValueError(f"unknown PDU model '{model}'; known models: {known_models()}")
    if yaml is None:
        raise ValueError("PyYAML is required to load PDU model files")

    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    unknown = sorted(set(spec) - set(CAPABILITY_FLAGS) - {"driver"})
    if unknown:
        raise ValueError(f"PDU model '{model}' file {path} sets unknown keys: {unknown}")

    driver = spec.get("driver")
    if not driver:
        raise ValueError(f"PDU model '{model}' file {path} must name a driver")

    return PduModel(
        key=model,
        driver=str(driver),
        capabilities={flag: bool(spec.get(flag)) for flag in CAPABILITY_FLAGS},
    )
