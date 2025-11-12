import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="🏗️ Půjčovna pracovních strojů", layout="wide")
st.title("🏗️ Půjčovna pracovních strojů")

# Kontrola, že Excel existuje
if not os.path.exists("IT.xlsx"):
    st.error("❌ Soubor 'IT.xlsx' nebyl nalezen ve stejné složce jako app.py. Nahraj ho do GitHub repozitáře.")
    st.stop()

# Načti Excel s ošetřením chyb
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("IT.xlsx", engine="openpyxl")
        df = df.rename(columns=lambda x: str(x).strip())
        return df
    except Exception as e:
        st.error(f"❌ Nepodařilo se načíst Excel: {e}")
        return None

df = load_data()

if df is None or df.empty:
    st.warning("⚠️ Soubor IT.xlsx byl načten, ale je prázdný nebo bez hlaviček.")
    st.write("Zkontroluj, že první řádek v Excelu obsahuje názvy sloupců (např. Název, Cena, Popis…).")
    st.stop()

# Zobraz první řádky
st.subheader("📋 Náhled dat")
st.dataframe(df.head(), use_container_width=True)

# Vyhledávání
search = st.text_input("🔍 Hledat podle textu (např. název, typ, popis):")
if search:
    df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False, na=False).any(), axis=1)]

# Filtrování podle ceny, pokud existuje sloupec s cenou
price_cols = [c for c in df.columns if any(k in c.lower() for k in ["cena", "price", "hodinova"])]
if price_cols:
    price_col = price_cols[0]
    try:
        df[price_col] = pd.to_numeric(df[price_col], errors="coerce")
        min_price, max_price = float(df[price_col].min()), float(df[price_col].max())
        cena_min, cena_max = st.slider("💰 Filtrovat podle ceny", min_price, max_price, (min_price, max_price))
        df = df[(df[price_col] >= cena_min) & (df[price_col] <= cena_max)]
    except Exception as e:
        st.warning(f"Nepodařilo se filtrovat podle ceny ({e})")

# Výsledky
st.write(f"### Výsledky ({len(df)} položek)")
st.dataframe(df, use_container_width=True)

# Stažení dat
st.download_button("⬇️ Stáhnout aktuální výběr (CSV)",
                   df.to_csv(index=False).encode("utf-8-sig"),
                   "pujcovna.csv", "text/csv")

st.info("💡 Pokud se stále nic nezobrazuje, zkontroluj první řádek Excelu – musí mít názvy sloupců.")
