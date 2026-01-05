from pathlib import Path
import pandas as pd
import streamlit as st

from pricing_engine.tariff_engine import TariffEngine
from pricing_engine.schemas import ContractType  # enums live here in your repo

DATA_ROOT = Path(__file__).parent
SAMPLE_DATA = DATA_ROOT / "sample_data"
CONFIG_PATH = DATA_ROOT / "config" / "base.yaml"

@st.cache_data
def load_archetypes():
    df = pd.read_csv(SAMPLE_DATA / "customer_archetypes.csv")
    for c in ["archetype_id", "name", "market", "commodity", "segment", "tariff_structure"]:
        df[c] = df[c].astype(str).str.strip()
    return df

@st.cache_resource
def get_engine():
    return TariffEngine.from_config(config_path=CONFIG_PATH, data_root=DATA_ROOT)

def main():
    st.title("ROI + NI All-In Tariff Builder")

    df = load_archetypes()
    engine = get_engine()

    archetype_id = st.selectbox(
        "Customer archetype",
        df["archetype_id"].tolist(),
        format_func=lambda x: df.loc[df["archetype_id"] == x, "name"].iloc[0],
    )

    year = st.number_input("Year", min_value=2020, max_value=2035, value=2026, step=1)
    contract_type = st.selectbox("Contract type", ["fixed", "indexed"], index=0)
    include_vat = st.checkbox("Include VAT", value=True)

    if st.button("Run Pricing"):
        result = engine.build_tariff_from_archetype_id(
            archetype_id=archetype_id,
            year=int(year),
            contract_type=ContractType(contract_type),
            include_vat=include_vat,
        )

        st.subheader("Quote Summary")
        st.write(f"Weighted energy-only: **{result.weighted_energy_only_eur_per_kwh:.5f} €/kWh**")
        st.write(f"Weighted all-in: **{result.weighted_all_in_eur_per_kwh:.5f} €/kWh**")
        st.write(f"Annual bill ex VAT: **€{result.estimated_annual_bill_ex_vat:,.2f}**")
        st.write(f"Annual bill inc VAT: **€{result.estimated_annual_bill_inc_vat:,.2f}**")

        st.subheader("Components")
        st.write(result)

if __name__ == "__main__":
    main()
