# User Guide – ROI + NI All-In Tariff Builder

This guide explains how a Business Pricing Analyst can use the tariff engine without needing to touch the code.

## 1. Inputs to maintain

You maintain four main input files under `sample_data/`:

1. **Wholesale curves**:
   - `wholesale_elec_<market>_<year>.csv`
   - `wholesale_gas_<market>_<year>.csv`
   - Columns: year, market, commodity, band, price_eur_per_mwh

2. **Shaping adders**:
   - `shaping_adders.csv`
   - Columns: year, market, commodity, band, adder_eur_per_mwh

3. **Loss factors**:
   - `losses.csv`
   - Columns: year, market, commodity, segment, band, loss_factor

4. **Pass-through charges**:
   - `pass_through_charges.csv`
   - Columns: region, commodity, segment, year, band, charge_type, name, unit, value, effective_from, effective_to, version

Customer archetypes are also configurable via `customer_archetypes.csv`.

> **Tip:** Treat these as “pricing tables” and keep them under source control (Git) so that you always know what changed.

## 2. Updating pass-through charges

When ESB Networks, NIE Networks or regulators publish updated tariffs:

1. Add a new row in `pass_through_charges.csv` for each updated charge:
   - Increase the `version` number.
   - Set `effective_from` to the start date of the new tariff year.
   - Set the `value` to the new €/MWh equivalent.

2. Close the previous version:
   - Update `effective_to` to the day before the new tariff starts.

3. Run tests and a quick tariff build to confirm:
   - No effective date overlaps.
   - Step-changes look reasonable (20–30% jumps should be explainable).

If the engine raises an error about overlaps or missing charges, fix the CSV before issuing quotes.

## 3. Running a quote (CLI)

Typical call:

```bash
python -m pricing_engine run \
  --market ROI \
  --segment SME \
  --tariff daynight \
  --year 2026 \
  --commodity ELEC \
  --contract fixed \
  --output-excel outputs/roi_sme_dn_2026.xlsx \
  --output-csv outputs/roi_sme_dn_2026.csv
```

What this does:

Uses the SME Day/Night electricity archetype for ROI, 2026.

Loads the relevant wholesale, losses and pass-through data.

Builds a cost stack by band.

Calculates weighted all-in €/kWh, estimated annual bill ex/incl VAT.

Writes:

A CSV with band-level breakdown.

An Excel workbook with:

Tariff_Build

Cost_Stack_Data

Quote_Summary

Change --contract indexed to get an indexed product with adders vs wholesale.

4. Reading the output

Console summary:

Market, segment, tariff, contract type

Annual consumption and standing charge

Weighted energy-only and all-in €/kWh

Annual bill ex/incl VAT

For indexed products, per-band “Index + X €/MWh” adders

CSV/Excel:

Band-level components in €/MWh and €/kWh

Annual consumption allocated by band

Annual cost contribution by band

Ready-to-chart cost stack data

5. Typical workflows
5.1 Updating tariffs after a network change

Update pass_through_charges.csv with new values and dates.

Run:

pytest


to ensure sanity checks pass.

Rebuild standard archetype quotes:

python -m pricing_engine run --market ROI --segment SME --tariff daynight --year 2026 --commodity ELEC --contract fixed --output-excel outputs/roi_sme_dn_2026_new.xlsx


Compare new outputs (Excel/CSV) with previous ones to see impact by band and by customer type.

5.2 Building a custom quote

For a non-standard customer:

Add a new row in customer_archetypes.csv with:

Market, segment, commodity, tariff structure.

Annual consumption and standing charge.

Band split (e.g. 70% peak, 30% offpeak).

Re-run the engine with that archetype (or extend the CLI to take --archetype-id if desired).

6. Limitations of the MVP

Pass-through charges are simplified to €/MWh. Real models often include:

€/kVA charges

€/day standing charges

Capacity and reactive components

Only 3 archetypes are provided as examples.

No optimisation against forward books or risk metrics yet.

These are intentionally out of scope for the first version but the architecture is designed so they can be added incrementally.
