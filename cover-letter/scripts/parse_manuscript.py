#!/usr/bin/env python3
import sys
import json

path = sys.argv[1]
text = ""

try:
    if path.lower().endswith('.pdf'):
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:15]:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
    elif path.lower().endswith('.docx'):
        import docx2txt
        text = docx2txt.process(path)
    else:
        with open(path, encoding='utf-8', errors='ignore') as f:
            text = f.read()
except Exception as e:
    print(json.dumps({"error": str(e), "text": ""}))
    sys.exit(1)

print(json.dumps({"text": text}))