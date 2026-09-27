"""Refresh and verify the allowlisted local release, without publishing a ZIP."""
import json
from check_release import ROOT, publishable_files, digest, validate


def main():
    validate(check_manifest=False)
    target=ROOT/'provenance/FILE_MANIFEST.json'
    data={'files':[{'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)}
        for p in publishable_files() if p!=target]}
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(validate(),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
