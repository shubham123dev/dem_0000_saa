from pathlib import Path
from scripts.validate_angular_phase3 import validate
ROOT=Path(__file__).resolve().parents[1]
def test_phase3_shell_contract()->None: assert validate(ROOT)==[]
def test_phase3_does_not_fake_agent_execution()->None:
 text='\n'.join(path.read_text(encoding='utf-8').lower() for path in (ROOT/'frontend/src/app/layout').rglob('*.html'))
 assert 'execution succeeded' not in text
 assert 'fake reasoning' not in text
