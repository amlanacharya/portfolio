import argparse
import os
from pathlib import Path

try:
    import markdown
except ImportError:
    markdown = None

try:
    from weasyprint import HTML
except Exception:
    HTML = None

try:
    import pdfkit
except Exception:
    pdfkit = None


def md_to_html(md_text: str) -> str:
    if markdown:
        return markdown.markdown(md_text, extensions=["fenced_code", "tables"])
    # minimal fallback
    return "<pre>" + md_text.replace("&", "&amp;").replace("<", "&lt;") + "</pre>"


def convert_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    content = src.read_text(encoding="utf-8")
    html_body = md_to_html(content)
    html = f"""<html><head><meta charset="utf-8"><style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    h1,h2,h3 {{ color: #0f172a; }}
    code, pre {{ background: #f3f4f6; padding: 4px 6px; border-radius: 4px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 6px; text-align: left; }}
    </style></head><body>{html_body}</body></html>"""

    if HTML:
        HTML(string=html).write_pdf(str(dst))
        return

    if pdfkit:
        try:
            pdfkit.from_string(html, str(dst))
            return
        except Exception:
            pass

    # If no PDF engine available, write HTML placeholder (user can still view).
    dst.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Markdown docs to PDF for PageIndex ingestion.")
    parser.add_argument("--src", default="docs_folder", help="Source folder containing .md files")
    parser.add_argument("--out", default="docs_folder/pdf", help="Output folder for generated PDFs")
    parser.add_argument("--dry-run", action="store_true", help="List files only")
    args = parser.parse_args()

    src_dir = Path(args.src)
    out_dir = Path(args.out)

    md_files = list(src_dir.glob("*.md"))
    if not md_files:
        print(f"No markdown files found in {src_dir}")
        return

    print(f"Found {len(md_files)} markdown files")
    for md_file in md_files:
        pdf_path = out_dir / (md_file.stem + ".pdf")
        if args.dry_run:
            print(f"[dry-run] {md_file} -> {pdf_path}")
            continue
        convert_file(md_file, pdf_path)
        print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()
