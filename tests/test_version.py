import re
from pathlib import Path
import resolute

def test_version_sync():
    """Ensure pyproject.toml version matches resolute.__version__."""
    # Find project root (where pyproject.toml lives)
    # Assuming tests/ is a subfolder of the root
    project_root = Path(__file__).parent.parent
    pyproject_path = project_root / "pyproject.toml"
    
    assert pyproject_path.exists(), f"Could not find pyproject.toml at {pyproject_path}"
    
    with open(pyproject_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Simple regex to find version = "x.y.z"
    # Matches: version = "0.3.1"
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    assert match is not None, "Could not find version string in pyproject.toml"
    
    pyproject_version = match.group(1)
    
    assert pyproject_version == resolute.__version__, (
        f"Version mismatch! "
        f"pyproject.toml says '{pyproject_version}', "
        f"but resolute.__init__ says '{resolute.__version__}'"
    )
