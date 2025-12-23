import fitz


def extract_text_from_pdf(file: bytes) -> str:
    doc = fitz.open(stream=file, filetype="pdf")
    text = ""

    for page in doc:
        text += page.get_text()

    return text


def extract_text_from_txt(file: bytes) -> str:
    doc = fitz.open(stream=file, filetype="txt")
    text = ""

    for page in doc:
        text += page.get_text()

    return text

