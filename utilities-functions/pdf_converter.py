import base64


def base64_to_pdf_bytes(pdf_base64: str) -> bytes:
    """
    Convert a base64-encoded PDF payload into raw PDF bytes.
    Supports plain base64 or data URLs like:
    data:application/pdf;base64,<payload>
    """
    if not pdf_base64 or not isinstance(pdf_base64, str):
        raise ValueError("pdf_base64 must be a non-empty string")

    normalized = pdf_base64.strip()
    if "," in normalized and normalized.lower().startswith("data:"):
        normalized = normalized.split(",", 1)[1].strip()

    try:
        pdf_bytes = base64.b64decode(normalized, validate=True)
    except Exception as exc:
        raise ValueError("Invalid base64 PDF payload") from exc

    # Basic PDF signature check (%PDF-)
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("Decoded payload is not a valid PDF document")

    return pdf_bytes
