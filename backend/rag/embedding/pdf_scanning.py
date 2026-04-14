import pdfplumber
import re

def scan_pdf_document(file_path):

    extracted_data = []

    with pdfplumber.open(file_path) as pdf:
        
        for i, page in enumerate(pdf.pages):
            text = page.extract_text(x_tolerance=1, y_tolerance=2)

            if text:
                clean_text = clean_extracted_text(text)

                metadata = {
                    "source": file_path.split("/")[-1],
                    "page_number":i+1,
                    "total_pages":len(pdf.pages),
                    "char_count":len(clean_text)
                }

                extracted_data.append({
                    "content":clean_text,
                    "metadata":metadata
                })
            
    return extracted_data

def clean_extracted_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text