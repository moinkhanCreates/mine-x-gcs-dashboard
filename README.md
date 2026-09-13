# ⛏️ MINE-X // Sub-Surface AI-Powered Tactical Mine Safety GCS

---

> [!IMPORTANT]
> **OPERATIONAL SAFETY NOTICE**
> MINE-X is a Surface Ground Control Station (GCS) telemetry system engineered for underground coal mine rescue rovers. Semantic color coding across this console is strictly reserved for status indicators (Safe, Caution, Warning, Critical) to comply with industrial Human-Machine Interface (HMI) standards in hazardous environments.

> [!WARNING]
> **EXPLOSION HAZARD ZONE**
> Underground coal mines contain volatile atmospheric mixtures ($CH_4$, $CO$, $H_2$). All sub-surface hardware modules must reside within **DGMS Ex-d Flameproof Enclosures** capable of withstanding internal explosion pressures up to $1.0\text{ MPa}$ without igniting surrounding ambient atmospheres.

---

## 📸 System Architecture Overview

```text
               +-------------------------------------------------------+
               |          UNDERGROUND HAZARD ZONE (ZONE 0 / 1)         |
               +-------------------------------------------------------+
                                           |
    [ Multi-Gas Sensor Array ]     [ 60GHz mmWave Vital ]     [ LWIR Thermal ]
   (CH4, CO, CO2, O2, H2, N2)     (Sub-Debris Breathing)    (8-14um Core)
               \                           |                          /
                +--------------------------+-------------------------+
                                           |
                            [ Rover Sensor Processing Unit ]
                                           |
                            [ Sub-1GHz Mesh Node (ESP-NOW) ]
                                           |
                                  (( 868MHz / 915MHz ))
                                           |
                    +----------------------+----------------------+
                    |                      |                      |
            [ Relay Node 1 ]       [ Relay Node 2 ]       [ Relay Node 3 ]
                    |                      |                      |
                    +----------------------+----------------------+
                                           |
               +-------------------------------------------------------+
               |              SURFACE CONTROL STATION (GCS)            |
               +-------------------------------------------------------+
                                           |
                        [ Sub-1GHz Master Gateway Receiver ]
                                           |
                        [ Streamlit Telemetry Console (app.py) ]
                                           |
                      [ Analytical Physics Engine (mine_analytics) ]

```

---

## 🔬 Mine Atmospheric Physics & Analytics Engine

The core analytical module (`mine_analytics.py`) calculates real-time spontaneous combustion indices, stoichiometric ratios, and explosive boundaries from raw sensor telemetry.

### 1. Graham's Ratio ($GR$) — Spontaneous Coal Combustion Indicator

Graham's Ratio measures carbon monoxide production relative to oxygen depletion. It isolates coal oxidation from normal mine background air movement:

$$GR = \frac{CO \text{ (ppm)} / 100}{\Delta O_2 \text{ (\% vol)}} = \frac{CO}{0.2093 \cdot N_2 - O_2}$$

Where $\Delta O_2$ represents the oxygen deficit calculated against normal ambient air proportions ($20.93\%$).

| Graham's Ratio Value | Atmospheric Evaluation State | Recommended Tactical Action |
| --- | --- | --- |
| **$GR < 0.4$** | `NORMAL_BACKGROUND` | Standard rover traversal & monitoring |
| **$0.4 \le GR < 0.5$** | `POSSIBLE_HEATING` | Increase telemetry sampling frequency |
| **$0.5 \le GR < 1.0$** | `SPONTANEOUS_HEATING_CONFIRMED` | Prepare ventilation seal contingency |
| **$1.0 \le GR < 2.0$** | `SERIOUS_ADVANCED_HEATING` | Halt rover; inspect seam heat signatures |
| **$2.0 \le GR < 3.0$** | `CRITICAL_HEATING_IMMINENT_FIRE` | Alert surface response units |
| **$GR \ge 3.0$** | `ACTIVE_MINE_FIRE_CONFIRMED` | Immediate evacuation of mesh sector |

---

### 2. Coward's Methane Explosibility Triangle

Methane ($CH_4$) explosibility depends strictly on the co-presence of Oxygen ($O_2$) and inert dilution gases ($N_2$). Methane is explosive only within specific boundary limits:

$$5.0\% \le CH_4 \le 15.0\% \quad \text{at ambient } O_2 \approx 20.93\%$$

The system calculates dynamically shifting explosibility curves:

* **Lower Explosive Limit (LEL Line):**
$$CH_4 = -0.1157 \cdot (O_2 - 12.1) + 5.9$$


* **Upper Explosive Limit (UEL Line):**
$$CH_4 = 1.5993 \cdot (O_2 - 12.1) + 5.9$$


* **Nose Limit ($O_2$ Critical Threshold):** At $O_2 < 12.1\%$, methane mixtures cannot explode regardless of $CH_4$ concentration unless additional oxygen/air is introduced.

> [!DANGER]
> **POTENTIALLY EXPLOSIVE ZONE ALERT**
> If $CH_4 > \text{UEL}$, the mixture is fuel-rich and non-explosive *in situ*. However, introducing fresh fresh-air ventilation drops $CH_4\%$ into the explosive triangle, triggering an underground explosion.

---

### 3. Multi-Ratio Fire Index Matrix

To eliminate false positives caused by diesel exhaust fumes or battery off-gassing, MINE-X cross-references four complementary geochemical indices:

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                      FIRE-RISK INDEX EVALUATION                          │
├──────────────────────┬───────────────────────────────────┬───────────────┤
│ Ratio Metric         │ Mathematical Formula              │ Target Range  │
├──────────────────────┼───────────────────────────────────┼───────────────┤
│ Young's Ratio        │ YR = CO2 / ΔO2                    │ < 0.25 Normal │
│ Jones & Trickett     │ JTR = (CO2 + 0.75*CO - 0.25*H2) / │ 0.5 - 0.9     │
│                      │       ΔO2                         │ Coal Fire     │
│ Oxides of Carbon     │ Ratio = CO / CO2                  │ < 0.02 Safe   │
│ Oxygen Deficiency    │ ΔO2 = (0.2093 * N2) - O2          │ Nominal ~0.0% │
└──────────────────────┴───────────────────────────────────┴───────────────┘

```

---

## 📡 Hardware & Sensor System Specifications

### 1. Sub-1GHz RF Mesh Relay Topology

* **Frequency Band:** $868\text{ MHz}$ / $915\text{ MHz}$ ISM Band (Sub-GHz propagation bypasses heavy coal/strata attenuation that degrades $2.4\text{ GHz}$ Wi-Fi).
* **Protocol:** ESP-NOW Connectionless MAC Layer protocol with dynamic multi-hop routing.
* **Auto-Drop Pod Deployer:** When received signal strength drops below $\text{RSSI} \le -82\text{ dBm}$, the rover automatically releases a wireless relay node onto the drift floor to maintain a line-of-sight telemetry link back to the shaft base.

### 2. Multi-Modal Perception & Vital Sensing

* **LWIR Thermal Sensor:** $8\text{--}14\text{ }\mu m$ radiometric microbolometer core for seeing through heavy smoke and detecting underground heating hotspots.
* **60GHz mmWave Radar:** FMCW Doppler radar capable of detecting sub-millimeter chest wall movements (respiration) of trapped personnel under dust and light debris cover.
* **Mie Scattering Compensation:** Real-time software filtering applied to optical gas sensors to account for high particulate coal dust concentration.

---

## 🛠️ Installation & Quickstart

### Prerequisites

* **Python 3.10+**
* `pip` package manager

### 1. Clone Repository & Environment Setup

```bash
# Clone the repository
git clone https://github.com/your-username/MINE-X.git
cd MINE-X

# Create and activate Python virtual environment
python -m venv venv

# Windows Command Prompt
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

```

### 2. Install Dependencies

```bash
pip install -r requirements.txt

```

### 3. Run GCS Dashboard

```bash
streamlit run app.py

```

The application will launch on `http://localhost:8501`.

---

## 📂 Project Structure

```text
MINE-X/
│
├── app.py                  # Streamlit Enterprise GCS UI dashboard
├── mine_analytics.py       # Mathematical engine for atmospheric mine physics
├── requirements.txt        # Core dependencies (streamlit, pandas, numpy, altair)
└── README.md               # Senior-level technical documentation

```

---

## ⚖️ Standards & Compliance References

* **DGMS (Directorate General of Mines Safety, India):** Guidelines for Flameproof Electrical Apparatus (Ex-d) in gassy coal mines.
* **IS/IEC 60079-1:** Explosive atmospheres - Part 1: Equipment protection by flameproof enclosures "d".
* **US Bureau of Mines (USBM) Bulletin 627:** Flammability characteristics of combustible gases and vapors (Coward Explosibility Triangle).

---

> **MINE-X GCS Dashboard** · *Built for industrial safety evaluation, emergency preparedness demonstration, and expert technical review.*
