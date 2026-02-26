# Entry point for Azure App Service
import sys
from pathlib import Path

# Add src to Python path for Azure deployment
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from scalper_today.api.app import app  # noqa: F401, E402

# Azure looks for 'app' or 'application' in this file
