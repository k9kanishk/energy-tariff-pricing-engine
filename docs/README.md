# ROI + NI All-In Tariff Builder with Pass-Through Charge Updater

This project is a production-style pricing engine for ESB Business Pricing teams. It builds all-in electricity and gas tariffs for ROI and NI across SME and I&C customer segments.

It is designed for **commercial pricing analysts** and **trading-aligned quants** who need:

- Fast turn-around on SME + I&C tenders
- Clear cost stacks (wholesale, shape, losses, networks, levies, margin, risk)
- A robust audit trail and configurable assumptions
- Easy maintenance when network and levy charges change

## High-level features

- **Markets**: Republic of Ireland (ROI) and Northern Ireland (NI)
- **Commodities**: Electricity and Gas
- **Segments**: SME, I&C
- **Tariff structures**: Flat, Day/Night, Peak/Offpeak
- **Contract types**: 1-year Fixed and Indexed (wholesale index + fixed adders)
- **Outputs**:
  - Band-level energy-only and all-in unit rates (€/MWh and €/kWh)
  - Weighted average tariff per archetype
  - Estimated annual bills (ex/incl VAT)
  - Price waterfall tables for cost stack charts
  - CSV and Excel exports

## Why pass-through charges matter

For ESB Business customers, most of the bill is **regulated or semi-regulated**:

- Network charges (DUoS/TUoS, use-of-system)
- Levies (renewables, PSO-style charges)
- Losses factors

Wholesale energy is volatile and traded; pass-throughs and losses are updated on a schedule by networks or regulators. Getting these wrong means:

- Mispriced tenders
- Margin leakage
- Complaints and rebills

This engine isolates pass-through charges in a **versioned library** so that updates are:

- Traceable by effective date and version
- Validated for overlaps and step-changes
- Easy to reprice across all archetypes and products

## Technical overview

The engine is written in **Python** using:

- `pandas` / `numpy` for data handling and calculations
- `pydantic` for typed schemas and validation
- `PyYAML` for config
- `openpyxl` / `xlsxwriter` for Excel export
- `pytest` for tests

### Architecture

- `pricing_engine/`
  - `schemas.py`: Enums and strongly-typed models for wholesale, losses, charges, tariffs.
  - `config.py`: Loads YAML configuration (`VAT`, margin/risk, sanity bounds, file paths).
  - `market_data.py`: Reads CSVs for wholesale curves, shaping adders, losses, archetypes.
  - `charges.py`: Pass-through library with effective date / versioning and change detection.
  - `tariff_engine.py`: Core pricing engine, fixed + indexed products, annual bill logic.
  - `waterfall.py`: Builds price waterfall datasets for analysis and charting.
  - `export_csv.py` / `export_excel.py`: Quote exports for pricing teams.
- `config/`: Central configuration.
- `sample_data/`: Stylised example data to run the model out of the box.
- `docs/`: Methodology, user guide, interview pitch.
- `tests/`: Pytest-based regression checks.

### Running locally

```bash
# 1. Create and activate a virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run a sample quote: ROI SME Elec Day/Night 2026
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

This will print a quote summary to the console and write tariff build / Excel outputs under outputs/.

For a quick visual front-end:

```bash
streamlit run streamlit_app.py
```
