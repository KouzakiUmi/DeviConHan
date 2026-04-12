# Modern Python Build Script (Optional)
# This script demonstrates how to use pyproject.toml for building
# Note: This project primarily uses PyInstaller for executable builds

#!/usr/bin/env python3
"""
Modern Python Build Script for Tyrano Patcher

This script shows how to use pyproject.toml for modern Python packaging.
For executable builds, use Pack.cmd (Windows) or Pack.sh (Mac/Linux) instead.
"""

import subprocess
import sys


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8+ required", file=sys.stderr)
        return False
    return True


def install_build():
    """Install build module if not available."""
    try:
        import build

        return True
    except ImportError:
        print("Installing build module...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "build"], check=True)
        return result.returncode == 0


def build_wheel():
    """Build wheel using modern Python packaging."""
    print("Building wheel...")
    result = subprocess.run([sys.executable, "-m", "build", "--wheel"], check=True)
    return result.returncode == 0


def build_sdist():
    """Build source distribution."""
    print("Building source distribution...")
    result = subprocess.run([sys.executable, "-m", "build", "--sdist"], check=True)
    return result.returncode == 0


def main():
    """Main build function."""
    print("Tyrano Patcher - Modern Python Build")
    print("====================================")

    if not check_python_version():
        return 1

    if not install_build():
        print("Failed to install build module", file=sys.stderr)
        return 1

    # Build wheel
    if not build_wheel():
        print("Wheel build failed", file=sys.stderr)
        return 1

    # Build source distribution
    if not build_sdist():
        print("Source distribution build failed", file=sys.stderr)
        return 1

    print("\nBuild complete! Check dist/ directory for artifacts.")
    print("\nNote: For executable builds, use Pack.cmd (Windows) or Pack.sh (Mac/Linux)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
