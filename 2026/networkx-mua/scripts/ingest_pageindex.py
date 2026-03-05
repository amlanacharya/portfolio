import argparse
import json
import os
from pathlib import Path
from typing import Dict, Any

import requests


API_URL = os.environ.get("PAGEINDEX_API_URL", "http://localhost:8080")
API_KEY = os.environ.get("PAGEINDEX_API_KEY")
SITE_ID = os.environ.get("PAGEINDEX_SITE_ID")
UPLOAD_ENDPOINT = os.environ.get("PAGEINDEX_UPLOAD_PATH", "/api/documents")

MANIFEST_PATH = Path("docs_folder/pageindex_manifest.json")


def load_manifest() -> Dict[str, Any]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def save_manifest(data: Dict[str, Any]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def upload_pdf(pdf_path: Path, force: bool = False) -> Dict[str, Any]:
    if not API_KEY or not SITE_ID:
        raise RuntimeError("PAGEINDEX_API_KEY and PAGEINDEX_SITE_ID must be set")

    url = f"{API_URL.rstrip('/')}{UPLOAD_ENDPOINT}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    files = {"file": (pdf_path.name, pdf_path.read_bytes(), "application/pdf")}
    data = {"site_id": SITE_ID, "metadata": json.dumps({"source": pdf_path.name})}

    resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload PDFs to PageIndex and track manifest.")
    parser.add_argument("--pdf-dir", default="docs_folder/pdf", help="Directory containing PDF files")
    parser.add_argument("--dry-run", action="store_true", help="List planned uploads only")
    parser.add_argument("--force", action="store_true", help="Reupload even if manifest has entry")
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir)
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {pdf_dir}. Run convert_md_to_pdf first.")
        return

    manifest = load_manifest()
    print(f"Found {len(pdf_files)} PDFs. Manifest has {len(manifest)} entries.")

    for pdf in pdf_files:
        key = pdf.name
        if key in manifest and not args.force:
            print(f"Skip {key} (already uploaded)")
            continue

        if args.dry_run:
            print(f"[dry-run] Would upload {key}")
            continue

        try:
            result = upload_pdf(pdf, force=args.force)
            manifest[key] = {"doc_id": result.get("id") or result.get("doc_id"), "uploaded_at": result.get("created_at")}
            print(f"Uploaded {key} -> {manifest[key]}")
        except Exception as exc:
            print(f"Failed to upload {key}: {exc}")

    if not args.dry_run:
        save_manifest(manifest)
        print(f"Manifest saved to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
