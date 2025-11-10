import subprocess
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent

def test_run_tests_sh_generates_json():
    script = ROOT / "runTests.sh"
    assert script.exists(), "runTests.sh not found in project root"

    # Run the script
    proc = subprocess.run(["bash", str(script)], cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        pytest.fail(f"runTests.sh failed (code {proc.returncode})\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

    out_dir = ROOT / "tests" / "out"
    assert out_dir.exists() and out_dir.is_dir(), f"No output directory: {out_dir}"

    json_files = list(out_dir.glob("*.json"))
    assert json_files, f"No JSON files generated in {out_dir}"

    # Verify each JSON file is valid JSON
    for jf in json_files:
        try:
            with jf.open(encoding="utf-8") as fh:
                json.load(fh)
        except Exception as e:
            pytest.fail(f"Invalid JSON in {jf}: {e}")