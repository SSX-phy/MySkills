#!/usr/bin/env python3
import sys
from docx import Document
from docx.shared import Pt

letter_text = sys.stdin.read().strip()
output_path = sys.argv[1]

doc = Document()

style = doc.styles['Normal']
style.font.name = 'Times New Roman'
style.font.size = Pt(12)

for para in letter_text.split('\n\n'):
    para = para.strip()
    if para:
        p = doc.add_paragraph(para)
        p.paragraph_format.space_after = Pt(6)

doc.save(output_path)
print(f"Saved: {output_path}")