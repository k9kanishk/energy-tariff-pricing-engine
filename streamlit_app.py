import streamlit as st

from pricing_engine.tariff_engine import TariffEngine
from pricing_engine.schemas import Commodity, ContractType, Market, Segment, TariffStructure
from pricing_engine.waterfall import tariff_components_to_dataframe


def main() -> None:
    st.title("ROI + NI All-In Tariff Builder")

    engine = TariffEngine.from_config("config/base.yaml", ".")

    col1, col2, col3 = st.columns(3)
    with col1:
        market = st.selectbox("Market", [m.value for m in Market], index=0)
        commodity = st.selectbox("Commodity", [c.value for c in Commodity], index=0)
    with col2:
        segment = st.selectbox("Segment", [s.value for s in Segment], index=0)
        tariff = st.selectbox("Tariff structure", [t.value for t in TariffStructure], index=1)
    with col3:
        year = st.number_input("Year", value=2026, step=1)
        contract = st.selectbox("Contract type", [c.value for c in ContractType], index=0)

    include_vat = st.checkbox("Include VAT in quote", value=True)

    if st.button("Run Pricing"):
        result = engine.build_tariff_from_archetype(
            market=Market(market),
            commodity=Commodity(commodity),
            segment=Segment(segment),
            tariff_structure=TariffStructure(tariff),
            year=int(year),
            contract_type=ContractType(contract),
            include_vat=include_vat,
        )

        st.subheader("Quote Summary")
        st.write(
            f"Weighted energy-only: **{result.weighted_energy_only_eur_per_kwh:.5f} €/kWh**"
        )
        st.write(f"Weighted all-in: **{result.weighted_all_in_eur_per_kwh:.5f} €/kWh**")
        st.write(f"Annual bill ex VAT: **€{result.estimated_annual_bill_ex_vat:,.2f}**")
        st.write(f"Annual bill inc VAT: **€{result.estimated_annual_bill_inc_vat:,.2f}**")

        st.subheader("Price Waterfall (€/MWh)")
        df = tariff_components_to_dataframe(result.components)
        st.dataframe(df)


if __name__ == "__main__":
    main()
