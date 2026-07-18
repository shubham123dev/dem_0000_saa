from pathlib import Path
from scripts.validate_angular_phase2 import contrast, validate
ROOT=Path(__file__).resolve().parents[1]
def test_phase2_hardening_contract()->None: assert validate(ROOT)==[]
def test_contrast_math_rejects_low_contrast()->None:
    assert contrast('#dd6f10','#ffffff')<4.5
    assert contrast('#dd6f10','#0f1012')>=4.5
