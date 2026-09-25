"""Build an allowlisted source ZIP and its file checksums. No remote publishing."""
from pathlib import Path
import argparse
import json
import zipfile
from check_release import ROOT, publishable_files, digest, validate


def build(output):
    output = Path(output).resolve()
    if ROOT in output.parents:
        raise ValueError("ZIP output must be outside the repository")
    if output.exists():
        raise FileExistsError(output)
    validate(check_manifest=False)
    manifest_file = ROOT / "provenance/FILE_MANIFEST.json"
    files = [p for p in publishable_files() if p != manifest_file]
    manifest = {"files": [{"file": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": digest(p)} for p in files]}
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    validation = validate()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in publishable_files():
            archive.write(path, str(Path("energy-topic-hotspots") / path.relative_to(ROOT)))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
    output.with_suffix(output.suffix + ".sha256").write_text(digest(output) + "  " + output.name + "\n")
    return {**validation, "zip": output.name, "zip_bytes": output.stat().st_size, "zip_sha256": digest(output)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output), ensure_ascii=False, indent=2))
