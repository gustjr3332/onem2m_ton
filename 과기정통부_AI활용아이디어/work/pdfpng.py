import fitz, sys
d=fitz.open(sys.argv[1]); print(d.page_count,"pages")
for i,p in enumerate(d): p.get_pixmap(dpi=int(sys.argv[3]) if len(sys.argv)>3 else 90).save(f"{sys.argv[2]}_{i}.png")
