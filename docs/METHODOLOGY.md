# Tariff Methodology & Audit Trail

This document explains how the pricing engine constructs all-in tariffs for ROI and NI SME and I&C customers.

## Scope and assumptions

- **Markets**: ROI and NI
- **Commodities**: Electricity and Gas
- **Customer segments**: SME, I&C
- **Tariff structures**:
  - SME Flat 24/7
  - SME Day/Night
  - I&C Peak/Offpeak
- **Contract types**:
  - 1-year Fixed price
  - Indexed: wholesale index + fixed adders for pass-through, losses, margin, risk
- **VAT**: Configurable rate by market (e.g. ROI 23%, NI 20%)

All numeric values supplied in the repository are **sample values only** and are clearly labelled as such. In production, these would be replaced with:

- Live wholesale curves from trading / risk systems
- Official network and levy tariffs from regulators and network operators
- ESB-specific margin and risk settings

## Units

- Wholesale, shaping, losses, network, levies, margin, risk: **€/MWh**
- Retail unit rates: **€/kWh** (values divided by 1,000)
- Consumption: **kWh per year**
- Standing charges: **€/year**

## Formulae

For a given band \(b\):

- \( W_b \) – Wholesale price in €/MWh
- \( S_b \) – Shaping adder in €/MWh
- \( LF_b \) – Loss factor (dimensionless, >= 1.0)
- \( N_b \) – Network charges in €/MWh
- \( L_b \) – Levies in €/MWh
- `margin_pct`, `risk_pct` – configured per segment

1. **Energy excluding losses**

\[
E^{\text{exloss}}_b = W_b + S_b
\]

2. **Losses component**

\[
\text{Losses}_b = E^{\text{exloss}}_b \cdot (LF_b - 1)
\]

3. **Subtotal before margin & risk**

\[
\text{Sub}_b = W_b + S_b + \text{Losses}_b + N_b + L_b
\]

4. **Margin and risk**

\[
\text{Margin}_b = \text{Sub}_b \cdot \text{margin\_pct}
\]
\[
\text{Risk}_b = \text{Sub}_b \cdot \text{risk\_pct}
\]

5. **Energy-only rate**

\[
\text{EnergyOnly}_b = W_b + S_b + \text{Losses}_b
\]

6. **All-in rate**

\[
\text{AllIn}_b = \text{EnergyOnly}_b + N_b + L_b + \text{Margin}_b + \text{Risk}_b
\]

7. **Convert to €/kWh**

\[
\text{EnergyOnly}_b^{\text{kWh}} = \frac{\text{EnergyOnly}_b}{1000}
\]
\[
\text{AllIn}_b^{\text{kWh}} = \frac{\text{AllIn}_b}{1000}
\]

## Weighted averages by archetype

Each customer archetype defines a **band split** (e.g. 60% Day, 40% Night).

For tariff structure \(T\) with bands \(b \in T\):

\[
\text{WA\_AllIn}^{\text{kWh}} = \sum_{b} w_b \cdot \text{AllIn}_b^{\text{kWh}}
\]

where \( w_b \) is the band share (sums to 1).

Annual bill (ex VAT):

\[
\text{Bill}_{\text{exVAT}} = \text{WA\_AllIn}^{\text{kWh}} \cdot Q + SC
\]

- \( Q \) – annual consumption (kWh)
- \( SC \) – standing charge (€/year)

Annual bill (incl VAT):

\[
\text{Bill}_{\text{incVAT}} = \text{Bill}_{\text{exVAT}} \cdot (1 + \text{VAT})
\]

## Fixed vs Indexed products

For **fixed** products, the wholesale price \(W_b\) is taken directly from the curve (e.g. trade-weighted baseload and peakload prices).

For **indexed** products:

- The engine sets \(W_b = 0\) within the numeric stack and calculates:
  - Energy-only adder: \( S_b + \text{Losses}_b \)
  - All-in adder: \( S_b + \text{Losses}_b + N_b + L_b + \text{Margin}_b + \text{Risk}_b \)
- These adders are stored in `IndexedTariffInfo` and presented as:

> All-in = Index + X €/MWh

for each band.

In production, the **index** could be EUPHEMIA DAM baseload/peakload or a bespoke ESB-linked index; the project is agnostic on that and focuses on the adders.

## Pass-through charge library and versioning

The `PassThroughLibrary`:

- Filters charges by:
  - Region (ROI/NI)
  - Commodity
  - Segment
  - Year
  - Band
  - `effective_from` / `effective_to` covering the pricing date
- Aggregates charges by type:
  - **NETWORK** – e.g. DUoS, TUoS, Use-of-System, capacity elements normalised to €/MWh
  - **LEVY** – e.g. renewable obligations, PSO-type levies

Validation:

1. **Overlap detection**  
   Within each charge key (region, commodity, segment, year, band, type, name), overlapping date ranges are flagged.

2. **Step-change detection**  
   Between consecutive versions, step changes > configured threshold (e.g. 20%) are flagged for review.

## Sanity checks

Before returning a tariff, the engine checks:

- All-in €/kWh per band is within configured bounds (per segment).
- Weighted all-in €/kWh is within bounds.

If any check fails, a `ValueError` is raised to prevent issuing a mispriced quote. This is intentional: **the engine fails closed** rather than silently leaking margin.

## Audit trail

For a given quote, you can reconstruct:

- Input data:
  - Wholesale curve rows used (year, band)
  - Loss factors
  - Pass-through charges (with names, values, versions)
  - Margin and risk settings
- Intermediate calculations:
  - Energy-only, network, levy, margin, risk, all-in €/MWh per band
- Outputs:
  - Band-level €/kWh
  - Weighted rates
  - Annual bill with and without VAT

The Excel outputs and CSV exports are suitable to attach directly to internal model approval or to answer “what if” questions from commercial and risk stakeholders.
