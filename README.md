# Medication Refill Calculator

[![Frontend: Vanilla JS](https://img.shields.io/badge/frontend-vanilla_js-orange.svg)](#architecture)
[![Deployment: Static](https://img.shields.io/badge/deployment-static_site-blue.svg)](#deployment)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Privacy: Stateless](https://img.shields.io/badge/Privacy-100%25_Stateless-success.svg)](#security--privacy)
[![Status: Production Ready](https://img.shields.io/badge/status-production_ready-success.svg)](#system-overview)

A high-performance, fully client-side medication refill calculator designed for accuracy, resilience, and privacy-first usage. Handles real-world messy inputs, edge cases, and clinical-style scenarios — entirely in the browser, with no data ever leaving the device.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Key Features](#key-features)
4. [Edge Case Handling](#edge-case-handling)
5. [Quick Start](#quick-start)
6. [Deployment](#deployment)
7. [Input Specifications](#input-specifications)
8. [Calculation Model](#calculation-model)
9. [Date Parsing Engine](#date-parsing-engine)
10. [Security & Privacy](#security--privacy)
11. [Limitations](#limitations)
12. [Future Improvements](#future-improvements)
13. [License & Disclaimers](#license--disclaimers)

---

## System Overview

The Medication Refill Calculator eliminates ambiguity in prescription tracking. Given a fill date, supply length, and optional dosage details, it instantly computes:

- Refill eligibility date
- Days remaining until refill
- Expected medication consumption
- Remaining pill supply

All computation runs **instantly in-browser** with no network requests of any kind.

**Core principles:**

| Principle | Implementation |
|---|---|
| Zero backend | Pure HTML/CSS/JS, no server required |
| Zero persistence | No localStorage, cookies, or analytics |
| Deterministic output | Same inputs always produce the same result |
| Fail-safe inputs | Invalid or partial inputs are handled gracefully |

---

## Architecture

**Stack:** HTML5 · CSS3 · Vanilla JavaScript (no frameworks or build tools)

**Execution model:** Fully client-side. No API calls, no bundler, no runtime dependencies.

```
User Input → In-Memory JS Calculation → UI Render
```

**Design goals:**

- Deterministic outputs
- Sub-millisecond compute time
- High input tolerance
- Mobile-first responsive layout

---

## Key Features

### Intelligent Input Handling
- Accepts a wide range of date formats (see [Date Parsing Engine](#date-parsing-engine))
- Handles partial or missing optional fields
- Automatically normalizes out-of-range numeric values

### Robust Calculation Engine
- Supports fractional dosing (e.g., 0.5 pills/day)
- Detects and resolves inconsistencies between entered quantity and day supply
- Prevents floating-point rounding drift

### Adaptive Refill Logic

Refill eligibility is calculated based on supply length:

| Supply Duration | Refill Rule |
|---|---|
| ≤ 7 days | Exact last day |
| ≤ 30 days | 2 days early |
| > 30 days | 10% buffer (floor) |

### Real-Time Supply Tracking
When quantity and pills/day are provided, the calculator also reports:
- Pills taken to date
- Pills remaining
- Days of supply remaining

### Safety & Validation
- Rejects future fill dates
- Clamps unrealistically large values
- Guards against `NaN` / `Infinity` propagation
- Issues warnings for extreme or suspicious inputs

---

## Edge Case Handling

| Scenario | Behavior |
|---|---|
| Future fill date | Rejected with error message |
| Extremely large quantities | Clamped to safe range + warning |
| Fractional dosing | Fully supported |
| Zero or missing dosing | Optional fields skipped gracefully |
| Very old prescriptions (> 10 years) | Warning issued |
| Extreme supply duration | Warning issued |
| `NaN` / `Infinity` values | Sanitized before any calculation |

---

## Quick Start

No build step, no dependencies, no installation required.

```bash
# Clone the repository
git clone https://github.com/yourusername/medication-refill-calculator.git
cd medication-refill-calculator

# Open directly in your browser
open index.html
```

Or double-click `index.html` — it works immediately in any modern browser.

---

## Deployment

This is a fully static app. No server configuration is needed.

**Recommended platforms:**

| Platform | Notes |
|---|---|
| [GitHub Pages](https://pages.github.com/) | Free, push-to-deploy |
| [Vercel](https://vercel.com/) | Zero-config static hosting |
| [Netlify](https://www.netlify.com/) | Drag-and-drop deploy supported |

**Deploy to GitHub Pages:**

```bash
git add .
git commit -m "deploy"
git push origin main
```

Then navigate to **Settings → Pages** in your repository and enable GitHub Pages on the `main` branch.

---

## Input Specifications

| Field | Required | Default | Description |
|---|---|---|---|
| Last Filled Date | Yes | — | The date the prescription was last filled. Accepts flexible formats. |
| Day Supply | No | 30 | Number of days the prescription is intended to last. |
| Total Pills | No | — | Total pill count dispensed. Enables supply tracking. |
| Pills per Day | No | — | Daily dosage. Supports decimals (e.g., `0.5`). |

Only the **Last Filled Date** is required. All other fields enhance the output but are optional.

---

## Calculation Model

### Core Variables

```
daysElapsed  = today − fillDate
currentDay   = daysElapsed + 1
impliedSupply = quantity ÷ takenPerDay
```

### Supply Resolution

If the entered day supply and the quantity-implied supply differ by more than 20%, the implied value is used:

```
if |impliedSupply − enteredSupply| / enteredSupply > 0.20:
    use impliedSupply
```

### Refill Date Rule

```
daySupply ≤ 7   →  refillDay = daySupply
daySupply ≤ 30  →  refillDay = daySupply − 2
daySupply > 30  →  refillDay = floor(daySupply × 0.9)
```

### Quantity Model

```
taken    = daysElapsed × takenPerDay
left     = max(0, quantity − taken)
daysLeft = left ÷ takenPerDay
```

---

## Date Parsing Engine

The parser accepts a broad range of inputs and is designed to be tolerant of human error.

**Supported formats:**

- Standard numeric formats: `MM/DD/YYYY`, `YYYY-MM-DD`, `M/D/YY`
- Natural language: `"today"`, `"yesterday"`
- Written-out dates: `"November 15, 2024"`, `"Nov 15"`
- Fuzzy month matching: `"Novmber"`, `"Febuary"` → corrected automatically

All parsing is deterministic and browser-safe, avoiding reliance on `Date.parse()` inconsistencies across environments.

---

## Security & Privacy

This application is **100% stateless by design.**

| Property | Status |
|---|---|
| Backend server | None |
| API calls | None |
| Cookies | None |
| localStorage / sessionStorage | None |
| Analytics or tracking | None |
| Data transmission | None — ever |

All computation occurs in active memory and is discarded when the tab is closed or refreshed. No user data is stored, logged, or transmitted under any circumstances.

---

## Limitations

This tool is **not a medical system** and is not a substitute for clinical prescription management software.

**Does not account for:**
- Variable or sliding-scale dosing schedules
- PRN (as-needed) medication usage
- Pharmacy-specific or insurance-mandated refill windows
- Controlled substance regulations

**Assumes:**
- Linear, consistent daily medication usage
- Perfect adherence to the prescribed dose

---

## Future Improvements

Planned enhancements include:

- Adherence scoring and missed-dose tracking
- Early refill risk flags
- Controlled substance indicators
- Multi-medication tracking
- Export to CSV / JSON
- Clinical-grade validation layer

---

## License & Disclaimers

**License:** [MIT](https://opensource.org/licenses/MIT)

**Medical Disclaimer:** This tool is for informational purposes only. It is not intended to be a substitute for professional medical advice, diagnosis, or treatment. Always consult a licensed healthcare provider regarding prescription management.

---

*Built for accuracy. Designed for trust.*
