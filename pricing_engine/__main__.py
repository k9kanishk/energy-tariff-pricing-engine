from __future__ import annotations

import argparse
from pathlib import Path

from .export_csv import export_tariff_to_csv
from .export_excel import export_tariff_to_excel
from .schemas import Commodity, ContractType, Market, Segment, TariffStructure
from .tariff_engine import TariffEngine


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pricing_engine", description="ROI + NI All-In Tariff Builder"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Build a tariff for a given segment")
    run_parser.add_argument("--market", choices=[m.value for m in Market], required=True)
    run_parser.add_argument("--segment", choices=[s.value for s in Segment], required=True)
    run_parser.add_argument("--tariff", choices=[t.value for t in TariffStructure], required=True)
    run_parser.add_argument("--year", type=int, required=True)
    run_parser.add_argument(
        "--commodity", choices=[c.value for c in Commodity], default=Commodity.ELEC.value
    )
    run_parser.add_argument(
        "--contract", choices=[c.value for c in ContractType], default=ContractType.FIXED.value
    )
    run_parser.add_argument(
        "--config-path",
        default="config/base.yaml",
        help="Path to YAML config file",
    )
    run_parser.add_argument(
        "--data-root",
        default=".",
        help="Root directory for input files (config is relative to this).",
    )
    run_parser.add_argument(
        "--output-excel",
        help="Path to Excel file to write quote (optional)",
    )
    run_parser.add_argument(
        "--output-csv",
        help="Path to CSV file to write tariff build (optional)",
    )
    run_parser.add_argument(
        "--exclude-vat",
        action="store_true",
        help="If set, estimated bill will be ex-VAT only.",
    )

    args = parser.parse_args()

    if args.command == "run":
        engine = TariffEngine.from_config(args.config_path, args.data_root)

        result = engine.build_tariff_from_archetype(
            market=Market(args.market),
            commodity=Commodity(args.commodity),
            segment=Segment(args.segment),
            tariff_structure=TariffStructure(args.tariff),
            year=int(args.year),
            contract_type=ContractType(args.contract),
            include_vat=not args.exclude_vat,
        )

        # Print a concise quote summary to stdout
        print("=== Tariff Quote Summary ===")
        print(
            f"Market: {result.request.market.value}, "
            f"Commodity: {result.request.commodity.value}, "
            f"Segment: {result.request.segment.value}, "
            f"Tariff: {result.request.tariff_structure.value}, "
            f"Contract: {result.request.contract_type.value}"
        )
        print(f"Annual consumption: {result.request.annual_consumption_kwh:,.0f} kWh")
        print(f"Standing charge: €{result.request.standing_charge_eur_per_year:,.2f}/year")
        print(
            f"Weighted energy-only rate: {result.weighted_energy_only_eur_per_kwh:.5f} €/kWh"
        )
        print(f"Weighted all-in rate:      {result.weighted_all_in_eur_per_kwh:.5f} €/kWh")
        print(f"Estimated annual bill (ex VAT): €{result.estimated_annual_bill_ex_vat:,.2f}")
        print(f"Estimated annual bill (inc VAT): €{result.estimated_annual_bill_inc_vat:,.2f}")

        if result.indexed_info is not None:
            print("\nIndexed product structure (adders vs index in €/MWh):")
            for band, adder in result.indexed_info.band_adders_all_in_eur_per_mwh.items():
                print(f"  {band.value}: INDEX + {adder:.2f} €/MWh all-in")

        # Optional file exports
        if args.output_csv:
            export_tariff_to_csv(result, args.output_csv)
            print(f"\nTariff build exported to CSV: {Path(args.output_csv).resolve()}")

        if args.output_excel:
            export_tariff_to_excel(result, args.output_excel)
            print(f"Excel quote exported to: {Path(args.output_excel).resolve()}")


if __name__ == "__main__":
    main()
