# energy-tariff-pricing-engine

ROI/NI **all-in tariff builder** (Electricity + Gas) with:
- customer archetypes (typical SME / I&C profiles)
- wholesale curve inputs (ROI and NI)
- shaping adders + losses
- pass-through charge library (network + levies, incl. standing/capacity where relevant)
- margin + risk adders
- Streamlit app that produces a **tender-style quote summary**, unit rates by band, a €/MWh **price waterfall**, and estimated annual bill breakdown.

---

## What the app produces

For a selected **Customer archetype + Year + Contract type** the app calculates:

- **Weighted energy-only unit rate** (€/kWh)
- **Weighted all-in unit rate** (€/kWh)
- **Estimated annual bill** (ex VAT and inc VAT)
- **Unit rates by band** (e.g., FLAT / DAY / NIGHT / PEAK / OFFPEAK)
- **Price waterfall (€/MWh)** showing each component:
  - Wholesale
  - Shaping
  - Losses
  - Network (pass-through)
  - Levies (pass-through)
  - Margin
  - Risk
- **Non-energy pass-through totals** where applicable (standing/capacity type charges)
- CSV download of the unit rates by band

---

## Project structure (important folders)

- `streamlit_app.py`  
  Streamlit UI (tender output + charts + CSV export)

- `pricing_engine/`  
  Core pricing logic (loading inputs, building tariffs, sanity checks)

- `sample_data/`  
  Small, versioned input set used by the app:
  - `customer_archetypes.csv`
  - `pass_through_charges.csv`
  - `shaping_adders.csv`
  - `losses.csv`
  - `fx_rates.csv` (needed for NI conversion)
  - `wholesale_elec_roi_2026.csv`
  - `wholesale_elec_ni_2026.csv`
  - `wholesale_gas_roi_2026.csv`
  - `wholesale_gas_ni_2026.csv`

- `data/raw/wholesale/semopx_day_ahead/`  
  Optional “raw” SEMOpx exports used to generate wholesale curves (not required to run the app if you already have `sample_data/wholesale_*.csv`).

- `scripts/build_wholesale_curve_semopx.py`  
  Utility to build the simplified wholesale curves from raw SEMOpx CSV exports.

---

## How the pricing model works (high level)

For each tariff **band** (FLAT / DAY / NIGHT / PEAK / OFFPEAK):

1. Load band wholesale price (EUR/MWh)
2. Add shaping adder (EUR/MWh)
3. Apply losses factor → losses component (EUR/MWh)
4. Add pass-through charges for that band:
   - network (EUR/MWh)
   - levies (EUR/MWh) and/or standing/capacity charges where applicable
5. Apply margin % and risk % on the subtotal
6. Convert to €/kWh and compute weighted averages using the archetype’s band split.
7. Estimate annual bill using:
   - annual consumption (kWh)
   - standing charge (€/year)
   - VAT rate (market-specific)

---

## Run locally

### 1) Create environment and install deps
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2) Run the Streamlit app
```bash
streamlit run streamlit_app.py
```

The app reads from `sample_data/` by default.

---

## Build wholesale curves from SEMOpx raw exports (optional)

If you downloaded multiple SEMOpx Day-Ahead CSV exports into:
`data/raw/wholesale/semopx_day_ahead/`

You can generate the simplified band curves like this.

**ROI electricity curve (Windows)**
```bat
python scripts\build_wholesale_curve_semopx.py --input-dir data\raw\wholesale\semopx_day_ahead --market ROI --year 2026 --out sample_data\wholesale_elec_roi_2026.csv
```

**NI electricity curve (Windows)**  
NI requires FX (GBP→EUR) and optionally a basis adjustment.

```bat
python scripts\build_wholesale_curve_semopx.py --input-dir data\raw\wholesale\semopx_day_ahead --market NI --year 2026 --out sample_data\wholesale_elec_ni_2026.csv --fx-path sample_data\fx_rates.csv --ni-basis-eur-per-mwh 3.0
```

Note: Raw exports are typically only a recent window (e.g., ~90 days). This project uses those as a proxy to build a simple curve by band. It is not a true forward curve.

---

## Sanity bounds

The engine can enforce sanity bounds (min/max €/kWh) per segment/commodity.

When enabled, out-of-range tariffs raise a ValueError.

When disabled, the tariff still prices but the output should be treated as a warning.

Bounds live in `config/base.yaml` under `sanity`.

---

## Assumptions / limitations (explicit)

- Wholesale curves are simplified to band averages derived from the available raw window (proxy).
- NI electricity conversion depends on the FX file coverage; missing dates can cause curve build failures.
- Pass-through charges are represented as a library (network/levies/standing/capacity) and may be simplified relative to full regulatory schedules.
- This is a pricing-engine MVP intended for learning + portfolio demonstration, not a production billing system.

---

## Typical workflow

1. Update raw SEMOpx exports (optional)
2. Rebuild wholesale curves (`scripts/build_wholesale_curve_semopx.py`)
3. Run the Streamlit app and generate tender outputs
4. Export unit rates CSV for downstream use

---

## License

MIT (or update as needed).
