"""Export helpers — PDF / Markdown / TXT generation (lazy imports)."""
import io


def _to_pdf(text_blocks: list[tuple[str, str]]) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    for heading, body in text_blocks:
        pdf.set_font("helvetica", "B", 13)
        pdf.cell(0, 10, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 6, body or "-")
        pdf.ln(6)
    return bytes(pdf.output())


def _blocks_from_result(result: dict) -> list[tuple[str, str]]:
    return [
        ("Title", result.get("title", "")),
        ("Summary", result.get("summary", "")),
        ("Action Items", result.get("action_items", "")),
        ("Key Decisions", result.get("key_decisions", "")),
        ("Open Questions", result.get("open_questions", "")),
        ("Full Transcript", result.get("transcript", "")),
    ]


def export_pdf(result: dict) -> io.BytesIO:
    buf = io.BytesIO(_to_pdf(_blocks_from_result(result)))
    buf.seek(0)
    return buf


def export_markdown(result: dict) -> str:
    lines = [f"# {result.get('title', 'Meeting')}", ""]
    for heading, body in _blocks_from_result(result)[1:]:
        lines.append(f"## {heading}")
        lines.append("")
        lines.append(body or "-")
        lines.append("")
    return "\n".join(lines)


def export_txt(result: dict) -> str:
    out = []
    for heading, body in _blocks_from_result(result):
        out.append(f"{heading.upper()}\n{'=' * len(heading)}\n{body or '-'}\n")
    return "\n".join(out)
