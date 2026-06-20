from app.utils.pdf_extractor import PageText
from app.utils.text_chunker import chunk_pages

# Fake a small 3-page document — use your own real contract text later
pages = [
    PageText(page_number=1, text="ARTICLE 1 DEFINITIONS\n\nThis Agreement is entered into by both parties..."),
    PageText(page_number=2, text="ARTICLE 2 OBLIGATIONS\n\nEach party shall indemnify and hold harmless the other party against any claims damages or liabilities arising from breach of this agreement and the indemnifying party shall bear all reasonable legal costs incurred in defense of such claims including attorney fees court costs and any settlement amounts agreed upon by both parties."),
    PageText(page_number=3, text="ARTICLE 3 TERMINATION\n\nThis agreement may be terminated by either party..."),
]

chunks = chunk_pages(pages, chunk_size=30, chunk_overlap=5, min_chunk_length=20)

print(f"Total chunks: {len(chunks)}\n")
for c in chunks:
    print(f"[idx={c.chunk_index}] page={c.page_number} chars={c.char_start}-{c.char_end}")
    print(f"  text: {c.text[:100]}")
    print()

true_boundaries = []
pos = 0
for p in pages:
    start = pos
    end = pos + len(p.text)
    true_boundaries.append((start, end, p.page_number))
    pos = end + len("\n\n")   # must match your actual join logic exactly

print("\nTrue page boundaries:")
for start, end, pn in true_boundaries:
    print(f"  page {pn}: chars {start}-{end}")

mismatches = 0
for c in chunks:
    actual_page = None
    for start, end, pn in true_boundaries:
        if start <= c.char_start < end:
            actual_page = pn
            break
    status = "OK" if actual_page == c.page_number else "MISMATCH"
    if status == "MISMATCH":
        mismatches += 1
    print(f"[idx={c.chunk_index}] reported={c.page_number} actual={actual_page} [{status}]")

print("\n--- Full chunk text for page 2 chunks ---")
for c in chunks:
    if c.page_number == 2:
        print(f"[idx={c.chunk_index}]: {c.text}")
        print()