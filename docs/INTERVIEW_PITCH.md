# Interview Pitch – Tariff Engine

## 1. One-liner

"I built a fully-auditable ROI + NI tariff engine that generates all-in SME and I&C electricity and gas tariffs from wholesale curves and pass-through charges, with a pass-through versioning library and Excel outputs tailored for ESB Business Pricing."

## 2. Business context

- ESB Business Pricing analysts need to respond quickly to SME and I&C tenders in ROI and NI.
- A large part of the end-customer price is pass-through:
  - DUoS/TUoS or use-of-system charges.
  - Levies and renewable obligations.
  - Loss factors.
- These change periodically and must be reflected consistently across all quotes.
- The engine treats these as structured data with effective dates and versions, ensuring:
  - No overlaps.
  - Clear audit trail.
  - Easy impact analysis when tariffs change.

## 3. What the project does

- Takes **wholesale curves**, **shaping adders**, **loss factors**, and **pass-through charges**.
- Builds energy-only and all-in tariffs (€/MWh and €/kWh) for:
  - SME Flat
  - SME Day/Night
  - I&C Peak/Offpeak
- Supports both:
  - **1-year fixed** prices.
  - **Indexed** products (wholesale index + fixed adders).
- Outputs:
  - Band-level breakdowns and price waterfall tables.
  - Weighted average rates for standard archetypes.
  - Estimated annual bills including VAT.
  - CSV and Excel files for use in tender documents.

## 4. How it’s built (tech detail – short)

- Python, with `pandas`/`numpy` for data, `pydantic` for schemas, `PyYAML` for config.
- `PassThroughLibrary` abstracts the messy bit of pass-through charges:
  - Handles effective-from/to dates and versions.
  - Flags overlapping periods and large step-changes.
- `TariffEngine`:
  - Works off typed `TariffRequest`.
  - Applies consistent formulas for wholesale, shape, losses, networks, levies, margin, risk.
  - Enforces sanity bounds on €/kWh before returning a quote.
- Exports:
  - CSV and Excel, with a sheet dedicated to cost stack data.
- Optional Streamlit UI for quick tariff comparison and visualisation.

## 5. Why it’s relevant to ESB

- Directly mirrors what ESB Business Pricing analysts do day-to-day for SME and I&C segments.
- Shows:
  - Understanding of ROI and NI market structure (wholesale + pass-through).
  - Focus on auditability and governance (versioned charges, sanity checks).
  - Ability to translate pricing logic into maintainable production-style code.
  - Appreciation of business users’ needs via Excel exports and a simple UI.

## 6. Discussion hooks

If they want to go deeper, I can talk about:

- Extensions:
  - Capacity-based network charges.
  - Intraday shaping profiles.
  - Risk-based margin calibration.
  - Portfolio-level P&L and hedge alignment.
- Integration:
  - Hooking the engine into trading risk systems and CRM tools.
  - Automating nightly refresh of wholesale curves and network tables.
