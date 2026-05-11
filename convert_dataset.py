import zipfile
import re
import json

def extract_qa_pairs(docx_path):
    with zipfile.ZipFile(docx_path, 'r') as z:
        xml = z.read('word/document.xml').decode('utf-8')

    rows = re.findall(r'<w:tr\b[^>]*>.*?</w:tr>', xml, re.DOTALL)
    
    pairs = []
    for row in rows:
        cells = re.findall(r'<w:tc>.*?</w:tc>', row, re.DOTALL)
        if len(cells) == 3:
            texts = []
            for c in cells:
                t = re.sub(r'<[^>]+>', ' ', c).strip()
                t = re.sub(r'\s+', ' ', t)
                texts.append(t)
            
            c0, english, twi = texts[0], texts[1], texts[2]
            
            # Skip header rows
            if 'English' in english and 'Twi' in twi:
                continue
            if not english or not twi:
                continue
            if english.startswith('Q:') or c0 == 'Ans':
                pairs.append({
                    "type": "question" if english.startswith('Q:') else "answer",
                    "english": english.replace('Q: ', '').replace('Asemmisa: ', '').strip(),
                    "twi": twi.strip()
                })
    
    # Now pair questions with answers
    dataset = []
    i = 0
    while i < len(pairs) - 1:
        if pairs[i]['type'] == 'question' and pairs[i+1]['type'] == 'answer':
            dataset.append({
                "instruction_en": pairs[i]['english'],
                "instruction_tw": pairs[i]['twi'],
                "response_en": pairs[i+1]['english'],
                "response_tw": pairs[i+1]['twi'],
                # Combined prompt-response for training
                "prompt": f"Question: {pairs[i]['english']}",
                "completion": pairs[i+1]['english'],
                "prompt_tw": f"{pairs[i]['twi']}",
                "completion_tw": pairs[i+1]['twi'],
            })
            i += 2
        else:
            i += 1
    
    return dataset

# Run it
dataset = extract_qa_pairs("Agriculture_Combined500_EnglishTwi.docx")

# Save as JSON
with open("agri_dataset.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

print(f"Done! Extracted {len(dataset)} Q&A pairs")
print("First entry preview:")
print(json.dumps(dataset[0], ensure_ascii=False, indent=2))