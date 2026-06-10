"""Build the HS6 -> Lall (2000) technological category lookup.

Inputs (pipeline/cache/):
  lall_hierarchy.pdf            UNCTAD "SITC rev.3 products, by technological
                                categories (Lall (2000))"
  JobID-84_Concordance_H4_to_S3.CSV
                                WITS concordance, HS2012 6-digit -> SITC rev.3

Outputs (data/):
  lookup_hs6_lall.csv           hs6, sitc3, lall_code
  dim_lall.csv                  lall_code, label_en, label_pt, tier
"""

import csv
import re
import subprocess
import sys
from pathlib import Path

CACHE = Path(__file__).parent / "cache"
DATA = Path(__file__).parent.parent / "data"

LALL_PT = {
    "LDC01": ("Produtos primários", "Primário"),
    "LDC02": ("Manufaturas baseadas em recursos: agroindustriais", "Baseado em recursos"),
    "LDC03": ("Manufaturas baseadas em recursos: outras", "Baseado em recursos"),
    "LDC04": ("Baixa tecnologia: têxteis, vestuário e calçados", "Baixa tecnologia"),
    "LDC05": ("Baixa tecnologia: outros produtos", "Baixa tecnologia"),
    "LDC06": ("Média tecnologia: automotiva", "Média tecnologia"),
    "LDC07": ("Média tecnologia: processos", "Média tecnologia"),
    "LDC08": ("Média tecnologia: engenharia", "Média tecnologia"),
    "LDC09": ("Alta tecnologia: eletrônica e elétrica", "Alta tecnologia"),
    "LDC10": ("Alta tecnologia: outras", "Alta tecnologia"),
    "LDC99": ("Produtos não classificados", "Não classificado"),
}

CATEGORY_RE = re.compile(r"^\s*(LDC\d{2})\s+(.+?)\s*$")
PRODUCT_RE = re.compile(r"^\s*(\d{3})\s+(.+?)\s*$")


def parse_lall_pdf(pdf_path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Return (sitc3_group -> lall_code, lall_code -> label_en)."""
    txt_path = pdf_path.with_suffix(".txt")
    subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), str(txt_path)], check=True
    )

    sitc_to_lall: dict[str, str] = {}
    labels: dict[str, str] = {}
    current = None
    for line in txt_path.read_text(encoding="utf-8").splitlines():
        m = CATEGORY_RE.match(line)
        if m:
            current = m.group(1)
            labels[current] = m.group(2)
            continue
        m = PRODUCT_RE.match(line)
        if m and current is not None:
            code = m.group(1)
            if code in sitc_to_lall and sitc_to_lall[code] != current:
                sys.exit(
                    f"SITC group {code} listed under both "
                    f"{sitc_to_lall[code]} and {current}"
                )
            sitc_to_lall[code] = current
    return sitc_to_lall, labels


def parse_concordance(csv_path: Path) -> dict[str, str]:
    """Return hs6 -> sitc3 5-digit code (both zero-padded strings)."""
    out: dict[str, str] = {}
    with open(csv_path, encoding="latin-1") as f:
        for row in csv.DictReader(f):
            hs6 = row["HS 2012 Product Code"].strip().zfill(6)
            sitc = row["SITC Revision 3 Product Code"].strip()
            out[hs6] = sitc
    return out


def main() -> None:
    sitc_to_lall, labels = parse_lall_pdf(CACHE / "lall_hierarchy.pdf")
    hs_to_sitc = parse_concordance(CACHE / "JobID-84_Concordance_H4_to_S3.CSV")

    if set(labels) != set(LALL_PT):
        sys.exit(f"category set mismatch: pdf has {sorted(labels)}")

    DATA.mkdir(exist_ok=True)
    unmapped = 0
    with open(DATA / "lookup_hs6_lall.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hs6", "sitc3", "lall_code"])
        for hs6, sitc in sorted(hs_to_sitc.items()):
            group = sitc[:3]
            lall = sitc_to_lall.get(group)
            if lall is None:
                lall = "LDC99"
                unmapped += 1
            w.writerow([hs6, sitc, lall])

    with open(DATA / "dim_lall.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["lall_code", "label_en", "label_pt", "tier"])
        for code in sorted(LALL_PT):
            label_pt, tier = LALL_PT[code]
            w.writerow([code, labels[code], label_pt, tier])

    print(
        f"lookup_hs6_lall.csv: {len(hs_to_sitc)} HS6 codes, "
        f"{len(sitc_to_lall)} SITC groups in hierarchy, "
        f"{unmapped} HS6 fell back to LDC99"
    )


if __name__ == "__main__":
    main()
