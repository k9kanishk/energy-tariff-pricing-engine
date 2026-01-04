# streamlit_app.py
from pathlib import Path
import pandas as pd
import streamlit as st

from pricing_engine.tariff_engine import TariffEngine
from pricing_engine.types import Market, Segment, Commodity, ContractType  # adjust imports to your enums

DATA_ROOT = Path(__file__).parent / "sample_data"   # or wherever your CSVs live

@st.cache_data
def load_archetypes():
    path = DATA_ROOT / "customer_archetypes.csv"
    df = pd.read_csv(path)
    # normalize strings to avoid whitespace bugs
    for c in ["market", "commodity", "segment", "tariff_structure", "archetype_id", "name"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    return df

def main():
    st.title("ROI + NI All-In Tariff Builder")

    df = load_archetypes()

    # Pick archetype FIRST (prevents invalid combos)
    archetype_map = dict(zip(df["archetype_id"], df["name"]))
    archetype_id = st.selectbox(
        "Customer Archetype",
        options=df["archetype_id"].tolist(),
        format_func=lambda x: archetype_map.get(x, x),
    )

    row = df[df["archetype_id"] == archetype_id].iloc[0]

    # Auto-fill the pricing dimensions from the archetype
    market = row["market"]
    segment = row["segment"]
    commodity = row["commodity"]
    tariff_structure = row["tariff_structure"]

    st.caption(f"Market: **{market}** | Segment: **{segment}** | Commodity: **{commodity}** | Tariff: **{tariff_structure}**")

    year = st.number_input("Year", min_value=2020, max_value=2035, value=2026, step=1)
    contract_type = st.selectbox("Contract type", options=["fixed", "indexed"], index=0)
    include_vat = st.checkbox("Include VAT in quote", value=True)

    engine = TariffEngine(data_root=DATA_ROOT)  # adjust to how you build engine

    if st.button("Run Pricing"):
        # If your engine currently selects archetype by market/segment/tariff,
        # change the engine to accept archetype_id directly (next section).
        result = engine.build_tariff_from_archetype_id(
            archetype_id=archetype_id,
            year=int(year),
            contract_type=ContractType(contract_type),
            include_vat=include_vat,
        )

        st.subheader("Quote Summary")
        st.write(f"Weighted energy-only: **{result.weighted_energy_only_eur_per_kwh:.5f} €/kWh**")
        st.write(f"Weighted all-in: **{result.weighted_all_in_eur_per_kwh:.5f} €/kWh**")
        st.write(f"Annual bill ex VAT: **€{result.annual_bill_ex_vat:,.2f}**")
        st.write(f"Annual bill inc VAT: **€{result.annual_bill_inc_vat:,.2f}**")

if __name__ == "__main__":
    main()
