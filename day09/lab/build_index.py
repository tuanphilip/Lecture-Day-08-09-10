import os
import re
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

DOCS_DIR = Path(__file__).parent / "data" / "docs"
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"

def preprocess_document(raw_text: str, filepath: str):
    lines = raw_text.strip().split("\n")
    metadata = {
        "source": filepath,
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
    }
    content_lines = []
    header_done = False

    for line in lines:
        if not header_done:
            if line.startswith("Source:"):
                metadata["source"] = line.replace("Source:", "").strip()
            elif line.startswith("Department:"):
                metadata["department"] = line.replace("Department:", "").strip()
            elif line.startswith("Effective Date:"):
                metadata["effective_date"] = line.replace("Effective Date:", "").strip()
            elif line.startswith("Access:"):
                metadata["access"] = line.replace("Access:", "").strip()
            elif line.startswith("==="):
                header_done = True
                content_lines.append(line)
            elif line.strip() == "" or line.isupper():
                continue
        else:
            content_lines.append(line)

    cleaned_text = "\n".join(content_lines)
    cleaned_text = re.sub(r"\r\n", "\n", cleaned_text)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    return {
        "text": cleaned_text,
        "metadata": metadata,
    }

def chunk_document(doc):
    text = doc["text"]
    base_metadata = doc["metadata"].copy()
    chunks = []
    sections = re.split(r"(===.*?===)", text)

    current_section = "General"
    current_section_text = ""

    for part in sections:
        if re.match(r"===.*?===", part):
            if current_section_text.strip():
                section_chunks = _split_by_size(
                    current_section_text.strip(),
                    base_metadata=base_metadata,
                    section=current_section,
                )
                chunks.extend(section_chunks)
            current_section = part.strip("= ").strip()
            current_section_text = ""
        else:
            current_section_text += part

    if current_section_text.strip():
        section_chunks = _split_by_size(
            current_section_text.strip(),
            base_metadata=base_metadata,
            section=current_section,
        )
        chunks.extend(section_chunks)

    return chunks

def _split_by_size(text: str, base_metadata: dict, section: str):
    chunk_chars = 400 * 4
    overlap_chars = 80 * 4
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks = []
    current_chunk_paragraphs = []
    current_length = 0

    for p in paragraphs:
        p_len = len(p)
        if current_chunk_paragraphs and current_length + p_len + 2 > chunk_chars:
            chunk_text = "\n\n".join(current_chunk_paragraphs)
            chunks.append({
                "text": chunk_text,
                "metadata": {**base_metadata, "section": section},
            })

            overlap_paras = []
            overlap_len = 0
            for op in reversed(current_chunk_paragraphs):
                if overlap_len + len(op) + (2 if overlap_paras else 0) <= overlap_chars:
                    overlap_paras.insert(0, op)
                    overlap_len += len(op) + (2 if len(overlap_paras) > 1 else 0)
                else:
                    break

            current_chunk_paragraphs = overlap_paras
            current_length = overlap_len

        current_chunk_paragraphs.append(p)
        current_length += p_len + (2 if len(current_chunk_paragraphs) > 1 else 0)

    if current_chunk_paragraphs:
        chunk_text = "\n\n".join(current_chunk_paragraphs)
        chunks.append({
            "text": chunk_text,
            "metadata": {**base_metadata, "section": section},
        })

    return chunks

def build():
    print(f"Building Day 09 index in {CHROMA_DB_DIR}")
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_or_create_collection(
        name="day09_docs",
        metadata={"hnsw:space": "cosine"}
    )

    model = SentenceTransformer("all-MiniLM-L6-v2")

    doc_files = list(DOCS_DIR.glob("*.txt"))
    total_chunks = 0
    for filepath in doc_files:
        print(f"  Indexing: {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")
        doc = preprocess_document(raw_text, str(filepath))
        chunks = chunk_document(doc)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath.stem}_{i}"
            embedding = model.encode(chunk["text"]).tolist()
            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk["text"]],
                metadatas=[chunk["metadata"]],
            )
        total_chunks += len(chunks)
        print(f"    → {len(chunks)} chunks indexed.")

    print(f"Index complete! Total chunks: {total_chunks}")

if __name__ == "__main__":
    build()
