from pathlib import Path
import pandas as pd
import streamlit as st

from pricing_engine.tariff_engine import TariffEngine

DATA_ROOT = Path(__file__).parent / "sample_data"

@st.cache_data
def load_archetypes():
    df = pd.read_csv(DATA_ROOT / "customer_archetypes.csv")
    for c in ["archetype_id","name","market","commodity","segment","tariff_structure"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    return df

def main():
    st.title("ROI + NI All-In Tariff Builder")

    df = load_archetypes()

    archetype_id = st.selectbox(
        "Customer Archetype",
        df["archetype_id"].tolist(),
        format_func=lambda x: df.loc[df["archetype_id"] == x, "name"].iloc[0]
    )

    row = df[df["archetype_id"] == archetype_id].iloc[0]
    market = row["market"]
    commodity = row["commodity"]
    segment = row["segment"]
    tariff_structure = row["tariff_structure"]

    st.caption(f"{market} | {segment} | {commodity} | {tariff_structure}")

    year = st.number_input("Year", min_value=2020, max_value=2035, value=2026, step=1)
    contract_type = st.selectbox("Contract type", ["fixed", "indexed"], index=0)
    include_vat = st.checkbox("Include VAT", value=True)

    engine = TariffEngine(data_root=DATA_ROOT)

    if st.button("Run Pricing"):
        result = engine.build_tariff_from_archetype(
            market=market,
            commodity=commodity,
            segment=segment,
            tariff_structure=tariff_structure,
            year=int(year),
            contract_type=contract_type,
            include_vat=include_vat,
        )
        st.write(result)

if __name__ == "__main__":
    main()
