import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
import datetime

st.set_page_config(page_title="🏗️ Půjčovna pracovních strojů", layout="centered")

st.title("🏗️ Půjčovna pracovních strojů")

@st.cache_data
def load_data():
    df_raw = pd.read_excel("IT.xlsx", header=None, engine="openpyxl").dropna(how="all")
    header = df_raw.iloc[0]
    df = df_raw[1:].copy()
    df.columns = header
    df = df.rename(columns=lambda x: str(x).strip())
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"❌ Chyba při načítání IT.xlsx: {e}")
    st.stop()

if df.empty:
    st.warning("Soubor IT.xlsx je prázdný nebo nemá data.")
    st.stop()

# Vyber stroj
st.subheader("🚜 Vyberte stroj k zapůjčení")
st.dataframe(df, use_container_width=True)

st.markdown("---")

# Výběr položky
stroj_list = df.iloc[:, 1].dropna().unique().tolist()
stroj = st.selectbox("Vyberte stroj:", stroj_list)

# Cena (pokus o detekci)
price_cols = [c for c in df.columns if "cena" in str(c).lower()]
if price_cols:
    cena_col = price_cols[0]
    cena_radek = df[df.iloc[:, 1] == stroj]
    cena = float(cena_radek[cena_col].values[0]) if not cena_radek.empty else 0
else:
    cena = st.number_input("Zadejte cenu za hodinu (Kč):", min_value=0.0, step=10.0)

hodiny = st.number_input("⏱️ Počet hodin pronájmu:", min_value=1, step=1)
celkem = cena * hodiny

st.write(f"💰 **Celková cena:** {celkem:.2f} Kč")

# Uživatelské údaje
st.markdown("---")
st.subheader("🧾 Fakturační údaje")
jmeno = st.text_input("Jméno a příjmení")
firma = st.text_input("Firma (nepovinné)")
email = st.text_input("E-mail")
datum = datetime.date.today().strftime("%d.%m.%Y")

# Generování faktury
if st.button("📄 Vygenerovat fakturu (PDF)"):
    if not jmeno or not email:
        st.error("Vyplňte prosím jméno a e-mail.")
    else:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 800, "Faktura za pronájem pracovního stroje")

        c.setFont("Helvetica", 12)
        c.drawString(50, 770, f"Datum: {datum}")
        c.drawString(50, 750, f"Zákazník: {jmeno}")
        if firma:
            c.drawString(50, 730, f"Firma: {firma}")
        c.drawString(50, 710, f"E-mail: {email}")

        c.line(50, 700, 550, 700)
        c.drawString(50, 680, f"Stroj: {stroj}")
        c.drawString(50, 660, f"Počet hodin: {hodiny}")
        c.drawString(50, 640, f"Cena za hodinu: {cena:.2f} Kč")
        c.drawString(50, 620, f"Celková cena: {celkem:.2f} Kč")
        c.line(50, 600, 550, 600)
        c.drawString(50, 570, "Děkujeme za využití našich služeb!")

        c.showPage()
        c.save()

        pdf = buffer.getvalue()
        st.download_button(
            label="⬇️ Stáhnout fakturu (PDF)",
            data=pdf,
            file_name=f"faktura_{jmeno.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )
