"""Responsive-design audit across all templates."""
import pathlib
import re

TPL = pathlib.Path("templates")
BASE = (TPL / "base.html").read_text()

# --- does base.html carry the viewport meta? ---
base_viewport = 'name="viewport"' in BASE
print(f"base.html viewport meta: {base_viewport}")
print("=" * 72)

rows = []
for path in sorted(TPL.glob("*.html")):
    s = path.read_text(errors="ignore")
    extends_base = "extends" in s[:200] and "base.html" in s[:300]

    # viewport: inherited from base OR own
    if extends_base:
        viewport = base_viewport
    else:
        viewport = 'name="viewport"' in s

    # media queries present?
    mqs = sorted(set(re.findall(r"@media[^{]*?", s)))
    n_mq = len(re.findall(r"@media", s))

    # hazard 1: fixed pixel widths big enough to overflow a 375px phone
    wide_fixed = re.findall(r"width:\s*(\d{3,5})px", s)
    wide_fixed = [int(w) for w in wide_fixed if int(w) >= 320]

    # hazard 2: min-width that forces horizontal scroll on phones
    min_wide = [int(m) for m in re.findall(r"min-width:\s*(\d{3,5})px", s) if int(m) >= 500]

    # hazard 3: raw <img> tags (no width guard visible near them)
    imgs = len(re.findall(r"<img\b", s))

    # hazard 4: <table> without an overflow wrapper nearby
    tables = len(re.findall(r"<table\b", s))
    tbl_wrapped = len(re.findall(r"overflow-x:\s*auto", s))

    rows.append({
        "name": path.name,
        "extends": extends_base,
        "viewport": viewport,
        "n_mq": n_mq,
        "wide_fixed": len(wide_fixed),
        "min_wide": len(min_wide),
        "imgs": imgs,
        "tables": tables,
        "overflow_x": tbl_wrapped,
        "_wide_vals": wide_fixed[:6],
    })

# print compact table
print(f"{'template':34} {'inh':>4} {'view':>4} {'@med':>4} {'fixW':>4} {'minW':>4} {'img':>4} {'tbl':>4} {'ovfX':>4}")
for r in rows:
    flag = ""
    if not r["viewport"]:
        flag += " ⛔NO-VIEWPORT"
    if r["tables"] > 0 and r["overflow_x"] == 0:
        flag += " ⚠tbl"
    if r["wide_fixed"] > 0:
        flag += f" ⚠fixed{r['_wide_vals']}"
    print(f"{r['name']:34} {str(r['extends'])[0]:>4} {str(r['viewport'])[0]:>4} "
          f"{r['n_mq']:>4} {r['wide_fixed']:>4} {r['min_wide']:>4} "
          f"{r['imgs']:>4} {r['tables']:>4} {r['overflow_x']:>4}{flag}")

no_vp = [r["name"] for r in rows if not r["viewport"]]
print(f"\ntemplates WITHOUT working viewport: {len(no_vp)} {no_vp}")
