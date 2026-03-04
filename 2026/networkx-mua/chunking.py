import os
import re
from typing import List, Dict


def load_and_chunk_docs(docs_folder: str) -> List[Dict[str, str]]:

    chunks = []
    
    for filename in os.listdir(docs_folder):
        if not filename.endswith('.md'):
            continue
            
        filepath = os.path.join(docs_folder, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        pattern = r'^## (.+)$'
        
        sections = re.split(pattern, content, flags=re.MULTILINE)
        

        
        preamble = sections[0].strip()
        if preamble:
            chunks.append({
                "text": preamble,
                "source": filename,
                "section": "preamble"
            })
        
        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                header_text = sections[i].strip()
                section_content = sections[i + 1].strip()
                
                if section_content: 
                    chunks.append({
                        "text": f"## {header_text}\n\n{section_content}",
                        "source": filename,
                        "section": header_text
                    })
    
    return chunks

# if __name__ == "__main__":
#     docs_folder = "2026/networkx-mua/docs_folder"
#     chunks = load_and_chunk_docs(docs_folder)
    
#     print(f"Total chunks: {len(chunks)}")
#     print()
    
#     for i, chunk in enumerate(chunks[:len(chunks)]):  
#         print(f"--- Chunk {i+1} ---")
#         print(f"Source: {chunk['source']}")
#         print(f"Section: {chunk['section']}")
#         print(f"Text preview: {chunk['text'][:100]}...")
#         print()

