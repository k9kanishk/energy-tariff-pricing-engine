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

        

if __name__ == "__main__":
    main()

import pandas as pd

# ---------- Quote Summary (Tender Output) ----------
st.header("Quote Summary (Tender Output)")

req = result.request

left, right = st.columns(2)
with left:
    st.markdown(f"**Market:** {req.market.value}")
    st.markdown(f"**Segment:** {req.segment.value}")
    st.markdown(f"**Commodity:** {req.commodity.value}")
    st.markdown(f"**Tariff structure:** {req.tariff_structure.value}")
with right:
    st.markdown(f"**Contract type:** {req.contract_type.value}")
    st.markdown(f"**Year:** {req.year}")
    st.markdown(f"**Annual consumption (kWh):** {req.annual_consumption_kwh:,.0f}")
    st.markdown(f"**Standing charge (€/year):** €{req.standing_charge_eur_per_year:,.2f}")

vat_rate = req.vat_rate or 0.0
st.markdown(f"**VAT rate:** {vat_rate*100:.1f}%")

st.subheader("Key Pricing Outputs")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Weighted energy-only (€/kWh)", f"{result.weighted_energy_only_eur_per_kwh:.5f}")
k2.metric("Weighted all-in (€/kWh)", f"{result.weighted_all_in_eur_per_kwh:.5f}")
k3.metric("Annual bill ex VAT (€)", f"{result.estimated_annual_bill_ex_vat:,.2f}")
k4.metric("Annual bill inc VAT (€)", f"{result.estimated_annual_bill_inc_vat:,.2f}")

# ---------- Unit Rates by Band ----------
st.subheader("Unit Rates by Band")

rows_rates = []
for c in result.components:
    rows_rates.append({
        "Band": c.band.value,
        "All-in (€/kWh)": c.all_in_eur_per_mwh / 1000.0,
        "Energy-only (€/kWh)": c.energy_only_eur_per_mwh / 1000.0,
        "All-in (€/MWh)": c.all_in_eur_per_mwh,
        "Energy-only (€/MWh)": c.energy_only_eur_per_mwh,
    })

df_rates = pd.DataFrame(rows_rates).sort_values("Band")
st.dataframe(df_rates, use_container_width=True)

# ---------- Price Waterfall (€/MWh) ----------
st.subheader("Price Waterfall (€/MWh)")

rows_stack = []
for c in result.components:
    rows_stack.append({
        "Band": c.band.value,
        "Wholesale": c.wholesale_eur_per_mwh,
        "Shaping": c.shaping_eur_per_mwh,
        "Losses": c.losses_eur_per_mwh,
        "Network": c.network_eur_per_mwh,
        "Levies": c.levies_eur_per_mwh,
        "Margin": c.margin_eur_per_mwh,
        "Risk": c.risk_eur_per_mwh,
        "All-in": c.all_in_eur_per_mwh,
    })

df_stack = pd.DataFrame(rows_stack).set_index("Band")
st.dataframe(df_stack, use_container_width=True)

# Stacked bar chart (Streamlit will stack automatically per category)
st.bar_chart(df_stack[["Wholesale","Shaping","Losses","Network","Levies","Margin","Risk"]])

# ---------- Annual Bill Breakdown ----------
st.subheader("Estimated Annual Bill Breakdown")

annual_kwh = req.annual_consumption_kwh
standing = req.standing_charge_eur_per_year

# Split annual kWh by band using the request band_split weights
bill_rows = []
energy_cost_total = 0.0

# Build a dict of band -> all-in €/kWh
band_allin_kwh = {c.band: (c.all_in_eur_per_mwh / 1000.0) for c in result.components}

for band, share in req.band_split.items():
    kwh = annual_kwh * float(share)
    rate = band_allin_kwh.get(band, 0.0)
    cost = kwh * rate
    energy_cost_total += cost
    bill_rows.append({
        "Band": band.value,
        "Share": float(share),
        "kWh": kwh,
        "All-in rate (€/kWh)": rate,
        "Energy cost (€)": cost,
    })

df_bill = pd.DataFrame(bill_rows).sort_values("Band")
st.dataframe(df_bill, use_container_width=True)

bill_ex_vat_calc = energy_cost_total + standing
bill_inc_vat_calc = bill_ex_vat_calc * (1.0 + vat_rate)

b1, b2, b3 = st.columns(3)
b1.metric("Energy cost (ex VAT)", f"€{energy_cost_total:,.2f}")
b2.metric("Standing charges (ex VAT)", f"€{standing:,.2f}")
b3.metric("Total bill (ex VAT)", f"€{bill_ex_vat_calc:,.2f}")

st.metric("Total bill (inc VAT)", f"€{bill_inc_vat_calc:,.2f}")


import io

out = io.StringIO()
df_rates.to_csv(out, index=False)
st.download_button(
    label="Download unit rates (CSV)",
    data=out.getvalue(),
    file_name=f"quote_unit_rates_{req.market.value}_{req.commodity.value}_{req.segment.value}_{req.year}.csv",
    mime="text/csv"
)
