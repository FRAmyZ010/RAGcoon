import pdfplumber

def scan_pdf(file_path):
    raw_text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            content = page.extract_text()
            if content:
                raw_text += content + "\n"
    return raw_text