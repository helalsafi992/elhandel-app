import streamlit as st

st.title("🔋 Elhandel – Dagligt signal")

# Input
vind = st.number_input("Vindproduktion (MW)", value=1600)
forbrug = st.number_input("Forbrug (MW)", value=5100)
import_mw = st.number_input("Import (MW)", value=150)

# Beregning
residual_load = forbrug - vind
signal = residual_load > 2450 and import_mw < 200

# Output
st.subheader("📊 Beregning")
st.write(f"Residual load: **{residual_load:.0f} MW**")
st.write(f"Import: **{import_mw:.0f} MW**")

if signal:
    st.success("✅ KØBSSIGNAL registreret")
    st.markdown("- Anbefalet køb: **03:00 eller 13:00**  \n- Anbefalet salg: **19:00**  \n- Forventet profit: **+0,40 til +0,90 kr/kWh**")
else:
    st.warning("❌ Ingen signal i morgen – ingen handel anbefalet.")
