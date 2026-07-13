<!-- GAP-009:COMPLETED -->
"""
tools/packager.py — Mod packaging tool for Steam Workshop / Paradox Forum distribution.
Validates the mod, creates a properly structured zip, and verifies the .mod metadata file.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any


def validate_mod_structure(mod_path: Path) -> list[str]:
    """Check a mod directory for common packaging issues. Returns list of warnings."""
    warnings: list[str] = []

    # Check for descriptor.mod
    descriptor = mod_path / "descriptor.mod"
    if not descriptor.exists():
        # Check for .mod files
        mod_files = list(mod_path.glob("*.mod"))
        if not mod_files:
            warnings.append("No descriptor.mod or .mod file found — mod may not load")
        else:
            descriptor = mod_files[0]

    # Check required directories
    required_dirs = ["common", "localisation"]
    for d in required_dirs:
        if not (mod_path / d).exists():
            warnings.append(f"Missing directory: {d}/ — mod may have no content")

    # Check for thumbnail
    thumbnail = mod_path / "thumbnail.png"
    if not thumbnail.exists():
        warnings.append("No thumbnail.png — Steam Workshop listing will have no image")

    # Check for large files (>100MB)
    for f in mod_path.rglob("*"):
        if f.is_file() and f.stat().st_size > 100 * 1024 * 1024:
            warnings.append(f"Large file: {f.relative_to(mod_path)} ({f.stat().st_size / (1024*1024):.0f} MB)")

    return warnings


def package_mod(
    mod_path: str | Path,
    output_path: str | Path | None = None,
    *,
    validate: bool = True,
) -> dict[str, Any]:
    """Package a HOI4 mod into a zip file for distribution.

    Args:
        mod_path: Path to the mod directory.
        output_path: Where to write the .zip file. Default: <mod_name>.zip in CWD.
        validate: If True, run structure validation before packaging.

    Returns:
        dict with path, size, file_count, warnings, and validation status.
    """
    mod_path = Path(mod_path).resolve()
    if not mod_path.exists():
        return {"success": False, "error": f"Mod path not found: {mod_path}"}

    # Find mod name
    mod_name = mod_path.name
    descriptor = mod_path / "descriptor.mod"
    if descriptor.exists():
        try:
            for line in descriptor.read_text(encoding="utf-8").splitlines():
                if line.startswith("name"):
                    mod_name = line.split("=", 1)[1].strip().strip('"')
                    break
        except Exception:
            pass

    # Validate
    warnings: list[str] = []
    if validate:
        warnings = validate_mod_structure(mod_path)

    # Determine output path
    if output_path is None:
        output_path = Path.cwd() / f"{mod_name}.zip"
    else:
        output_path = Path(output_path)

    # Create zip
    file_count = 0
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(mod_path.rglob("*")):
            if f.is_file():
                # Skip hidden files and caches
                if any(part.startswith(".") for part in f.parts):
                    continue
                if "__pycache__" in str(f) or f.suffix in (".pyc", ".pyo"):
                    continue
                arcname = str(f.relative_to(mod_path))
                zf.write(f, arcname)
                file_count += 1

    size_mb = output_path.stat().st_size / (1024 * 1024)

    return {
        "success": True,
        "mod_name": mod_name,
        "output": str(output_path),
        "size_mb": round(size_mb, 2),
        "file_count": file_count,
        "warnings": warnings,
        "valid": len([w for w in warnings if "may not load" in w or "missing" in w.lower()]) == 0,
    }


# CLI entry point
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Package a HOI4 mod for distribution")
    parser.add_argument("mod_path", help="Path to the mod directory")
    parser.add_argument("--output", "-o", help="Output zip path", default=None)
    parser.add_argument("--no-validate", action="store_true", help="Skip validation")
    args = parser.parse_args()

    result = package_mod(args.mod_path, args.output, validate=not args.no_validate)
    print(json.dumps(result, indent=2))
