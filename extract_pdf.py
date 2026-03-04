import fitz
import sys

pdf_path = sys.argv[1] if len(sys.argv) > 1 else '/home/medaly/Desktop/MyWork/SOA-CLI/papers/doc.pdf'
doc = fitz.open(pdf_path)
text = ""
for page in doc:
    text += page.get_text()
print(text)
