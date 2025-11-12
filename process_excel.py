"""
process_excel.py
Skript pro načtení a "rozumné" zpracování Excelu podobného IT.xlsx,
kde nejsou správné hlavičky (např. Unnamed: x). Skript:
 - najde řádek který pravděpodobně obsahuje hlavičky,
 - použije ho jako hlavičky,
 - očistí názvy sloupců (diakritika, mezery -> snake_case),
 - automaticky navrhne mapování důležitých polí (name, price, description, available_from, available_to, id),
 - uloží "clean" Excel a CSV a vypíše navržené mapování.

Spusť: python process_excel.py
"""
import pandas as pd
import re
from pathlib import Path
from datetime import datetime

INPUT = "IT.xlsx"           # název vstupního souboru (musí být ve stejné složce jako skript)
CLEAN_XLSX = "IT_cleaned.xlsx"
CLEAN_CSV = "IT_cleaned.csv"

def slugify(s: str) -> str:
    s = str(s)
    s = s.strip().lower()
    # remove diacritics roughly (keep simple)
    s = s.replace("á","a").replace("č","c").replace("ď","d").replace("é","e").replace("ě","e")
    s = s.replace("í","i").replace("ň","n").replace("ó","o").replace("ř","r").replace("š","s")
    s = s.replace("ť","t").replace("ů","u").replace("ú","u").replace("ž","z")
    s = re.sub(r"[^\w\s\-]","",s)
    s = re.sub(r"\s+","_",s)
    s = re.sub(r"_+","_",s)
    return s

def find_header_row(df):
    """Najde index řádku, který je pravděpodobně hlavička: 
    hledáme první řádek s >50% ne-prázdnými buňkami."""
    ncols = df.shape[1]
    for i in range(0, min(10, df.shape[0])):  # prohledáme první 10 řádků
        nonnull = df.iloc[i].count()
        if nonnull >= max(1, ncols // 2):
            return i
    # fallback: 0
    return 0

def suggest_mapping(df):
    """Jednoduché heuristiky pro namapování sloupců na očekávaná pole."""
    mapping = {}
    cols = list(df.columns)
    lower = [c.lower() for c in cols]

    # heuristika podle jména sloupce
    def find_by_keywords(keywords):
        for i,c in enumerate(lower):
            for k in keywords:
                if k in c:
                    return cols[i]
        return None

    mapping['name'] = find_by_keywords(['name','nazev','název','půjčovna','produkt','product','title']) or cols[0]
    mapping['id'] = find_by_keywords(['id','kod','číslo','cislo','sku']) 
    mapping['description'] = find_by_keywords(['desc','popis','detai','pozn','note'])
    mapping['hourly_rate'] = find_by_keywords(['price','cena','rate','hod','hour'])
    mapping['available_from'] = find_by_keywords(['available_from','dostupne_od','od','from','start','datum'])
    mapping['available_to'] = find_by_keywords(['available_to','dostupne_do','do','to','end'])

    # další heuristika: pokud sloupec obsahuje hlavně čísla, může být cena
    for c in cols:
        s = df[c].dropna().astype(str)
        if len(s)>0:
            numeric_ratio = s.apply(lambda x: bool(re.match(r"^[0-9]+([.,][0-9]{1,2})?$", x.strip()))).mean()
            if numeric_ratio > 0.6 and mapping.get('hourly_rate') is None:
                mapping['hourly_rate'] = c

    # pokud id není nalezen, vezmeme první sloupec
    if mapping.get('id') is None:
        mapping['id'] = cols[0]

    # pokud description není, zkombinujeme Unnamed sloupce
    if mapping.get('description') is None:
        # hledáme nějaký Unnamed nebo druhej sloupec
        for c in cols:
            if 'unnamed' in c.lower() or 'popis' in c.lower():
                mapping['description'] = c
                break

    return mapping

def main():
    p = Path(INPUT)
    if not p.exists():
        print(f"Soubor {INPUT} nebyl nalezen ve složce. Vlož ho prosím do stejné složky jako tento skript a spusť znovu.")
        return

    # načteme bez hlavičky (header=None), abychom mohli najít skutečnou hlavičku
    df_raw = pd.read_excel(p, header=None, engine="openpyxl")
    print(f"Načteno {df_raw.shape[0]} řádků × {df_raw.shape[1]} sloupců (bez hlavičky).")

    header_row = find_header_row(df_raw)
    print(f"Navržený řádek s hlavičkami: index {header_row} (počítáno od 0).")

    header = df_raw.iloc[header_row].fillna("").astype(str).tolist()
    data = df_raw.iloc[header_row+1:].reset_index(drop=True).copy()
    data.columns = header

    # očistíme názvy sloupců
    clean_cols = [slugify(c) if c.strip()!="" else f"col_{i}" for i,c in enumerate(data.columns)]
    rename_map = {old:new for old,new in zip(data.columns, clean_cols)}
    data = data.rename(columns=rename_map)

    print("Očištěné názvy sloupců:")
    for i,c in enumerate(data.columns):
        print(f" - {i:02d}: {c}")

    # Nabídneme jednoduché mapování na pole, která budeme chtít v aplikaci/databázi
    suggested = suggest_mapping(data)
    print("\nNavržené mapování klíčových polí (můžeš ho později upravit):")
    for k,v in suggested.items():
        print(f"  {k:14s} -> {v}")

    # Pokusíme se převést možné datové sloupce
    for col in [suggested.get('available_from'), suggested.get('available_to')]:
        if col in data.columns:
            try:
                data[col] = pd.to_datetime(data[col], errors='coerce').dt.date
            except Exception:
                pass

    # pokus o převod ceny na číslo
    price_col = suggested.get('hourly_rate')
    if price_col in data.columns:
        # očistíme pomlčky, měny, čárky
        data[price_col] = data[price_col].astype(str).str.replace(r"[^\d\.,-]", "", regex=True).str.replace(",", ".", regex=False)
        # konverze
        data[price_col] = pd.to_numeric(data[price_col], errors='coerce')

    # Uložíme čistý soubor
    data.to_excel(CLEAN_XLSX, index=False)
    data.to_csv(CLEAN_CSV, index=False, encoding='utf-8-sig')

    print(f"\nHotovo — uložený očistěný soubor: {CLEAN_XLSX} a {CLEAN_CSV}")
    print("Otevři IT_cleaned.xlsx v Excelu a zkontroluj, zda hlavičky a data sedí.")
    print("Pokud chceš, můžeš mi sem zkopírovat seznam sloupců z 'IT_cleaned.xlsx' a já ti připravím další krok (např. generování katalogu, filtrování nebo export rezervací).")

if __name__ == "__main__":
    main()
