```markdown
# Underground Mine Safety & Rescue Rover : GCS Telemetry Dashboard

<p align="center">
  <img src="https://img.shields.io/badge/Status-GCS%20Development-007ACC?style=flat-square&logo=streamlit&logoColor=white" alt="Status">
  <img src="https://img.shields.io/badge/Stack-Python%20%7C%20Streamlit-E05252?style=flat-square&logo=python&logoColor=white" alt="Stack">
  <img src="https://img.shields.io/badge/Scope-Surface%20GCS%20%26%20Analytics-D97706?style=flat-square&logo=dashboard&logoColor=white" alt="Scope">
  <br>
  <img src="https://img.shields.io/badge/SIH-PS%2026039-4B5563?style=flat-square" alt="SIH PS">
  <img src="https://img.shields.io/badge/Compliance-DGMS%20Ex--d%20Standards-10B981?style=flat-square" alt="Compliance">
</p>

<p align="center">
  <b>Surface Ground Control Station · Fire Risk Analytics Engine · SIH 2026</b>
</p>

<p align="center">
  <i>Ground Control Station (GCS) console and real-time telemetry analytics platform for an underground mine safety and rescue rover, developed for Smart India Hackathon Problem Statement 26039 — <b>AI-Powered Underground Mine Safety, Monitoring and Rescue System</b> (Government of Jharkhand, Department of Higher & Technical Education).</i>
</p>

---

> [!IMPORTANT]
> **INDUSTRIAL HMI DESIGN CONVENTION**  
> MINE-X uses an enterprise industrial-console visual hierarchy (navy chrome, flat bordered panels). Semantic color highlights (amber, red, green, blue) are strictly reserved for operational status (caution, critical hazard, nominal, link status) rather than decorative UI themes.

---

## 📸 System Architecture

```text
  +-----------------------------------------------------------------------+
  |               UNDERGROUND HAZARD ZONE (ZONE 0 / ZONE 1)               |
  +-----------------------------------------------------------------------+
        │                           │                           │
  [ Gas Sensor Array ]      [ 60GHz mmWave Radar ]      [ LWIR Thermal Core ]
  (CH4, CO, CO2, O2, H2)    (Sub-Debris Respiration)    (8-14μm Hotspots)
        │                           │                           │
        +---------------------------+---------------------------+
                                    │
                  [ Rover Sensor Processing Node ]
                                    │
                  [ Sub-1GHz Mesh Unit (868MHz) ]
                                    │
                         (( Sub-Surface Mesh ))
                                    │
          +-------------------------+-------------------------+
          │                         │                         │
  [ Mesh Relay Pod 1 ]      [ Mesh Relay Pod 2 ]      [ Mesh Relay Pod 3 ]
          │                         │                         │
          +-------------------------+-------------------------+
                                    │
  +-----------------------------------------------------------------------+
  |                     SURFACE GROUND CONTROL STATION                    |
  +-----------------------------------------------------------------------+
                                    │
                       [ Master Mesh Gateway Node ]
                                    │
                     [ Streamlit UI Console (app.py) ]
                                    │
                   [ Physics Engine (mine_analytics.py) ]

```

---

## 🔬 Mine Atmospheric Physics & Analytics Engine

The analytical module (`mine_analytics.py`) calculates real-time spontaneous combustion indices, stoichiometric ratios, and explosive boundaries from raw sub-surface sensor telemetry.

### 1. Graham's Ratio ($GR$) — Spontaneous Coal Heating Indicator

Graham's Ratio measures carbon monoxide formation relative to oxygen depletion, isolating active coal seam oxidation from background atmospheric changes:

$$GR = \frac{CO \text{ (ppm)} / 100}{\Delta O_2 \text{ (\% vol)}} = \frac{CO}{0.2093 \cdot N_2 - O_2}$$

Where $\Delta O_2$ represents the oxygen deficit calculated against normal ambient air proportions ($20.93\%$).

| Graham's Ratio Value | Atmospheric Evaluation State | Recommended Tactical Action |
| --- | --- | --- |
| **$GR < 0.4$** | `NORMAL_BACKGROUND` | Standard rover traversal & routine sensing |
| **$0.4 \le GR < 0.5$** | `POSSIBLE_HEATING` | Increase mesh telemetry sampling rate |
| **$0.5 \le GR < 1.0$** | `SPONTANEOUS_HEATING_CONFIRMED` | Prepare ventilation sealing protocols |
| **$1.0 \le GR < 2.0$** | `SERIOUS_ADVANCED_HEATING` | Halt rover; inspect seam thermal signatures |
| **$2.0 \le GR < 3.0$** | `CRITICAL_HEATING_IMMINENT_FIRE` | Alert surface emergency response team |
| **$GR \ge 3.0$** | `ACTIVE_MINE_FIRE_CONFIRMED` | Immediate evacuation of targeted mesh zone |

---

### 2. Coward's Methane Explosibility Triangle

Methane ($CH_4$) explosibility depends on the proportional presence of Oxygen ($O_2$) and inert dilution gases ($N_2$). Methane is explosive only within specific boundary limits:

$$5.0\% \le CH_4 \le 15.0\% \quad \text{at ambient } O_2 \approx 20.93\%$$

The engine continuously evaluates dynamically shifting explosibility curves:

* **Lower Explosive Limit (LEL Line):**
$$CH_4 = -0.1157 \cdot (O_2 - 12.1) + 5.9$$


* **Upper Explosive Limit (UEL Line):**
$$CH_4 = 1.5993 \cdot (O_2 - 12.1) + 5.9$$


* **Nose Limit ($O_2$ Critical Threshold):** Below $12.1\% \text{ } O_2$, methane mixtures cannot explode regardless of $CH_4$ concentration unless fresh oxygen is introduced.

> [!WARNING]
> **POTENTIALLY EXPLOSIVE ZONE ALERT**
> If $CH_4 > \text{UEL}$, the atmospheric mixture is fuel-rich and non-explosive *in situ*. However, introducing fresh-air ventilation dilutes $CH_4\%$ directly into the explosive triangle, triggering an ignition risk.

---

### 3. Multi-Ratio Fire Index Matrix

To eliminate false positives caused by battery off-gassing or diesel fumes, MINE-X cross-references four complementary geochemical indices:

| Ratio Metric | Mathematical Formula | Target Nominal Range |
| --- | --- | --- |
| **Young's Ratio** | $YR = \frac{CO_2}{\Delta O_2}$ | $< 0.25$ Normal |
| **Jones & Trickett** | $JTR = \frac{CO_2 + 0.75 \cdot CO - 0.25 \cdot H_2}{\Delta O_2}$ | $0.5 \text{ -- } 0.9$ Coal Fire |
| **Oxides of Carbon** | $Ratio = \frac{CO}{CO_2}$ | $< 0.02$ Safe |
| **Oxygen Deficiency** | $\Delta O_2 = (0.2093 \cdot N_2) - O_2$ | Nominal $\approx 0.0\%$ |

---

## 📡 Sub-Surface Hardware & Communication Specs

### 1. Sub-1GHz RF Mesh Relay Topology

* **Frequency Band:** $868\text{ MHz}$ / $915\text{ MHz}$ ISM Band (Sub-GHz propagation bypasses strata attenuation that degrades $2.4\text{ GHz}$ Wi-Fi).
* **Protocol:** ESP-NOW Connectionless MAC Layer with dynamic multi-hop routing.
* **Auto-Drop Pod Deployer:** When received signal strength drops below $\text{RSSI} \le -82\text{ dBm}$, the rover releases a wireless relay node to maintain a continuous telemetry link back to the shaft base.

### 2. Multi-Modal Perception & Vital Sensing

* **LWIR Thermal Sensor:** $8\text{--}14\text{ }\mu m$ radiometric microbolometer core for penetrating dense smoke and locating sub-surface heat sources.
* **60GHz mmWave Radar:** FMCW Doppler radar capable of detecting sub-millimeter chest wall movements (respiration) of trapped personnel under dust and light debris cover.
* **Mie Scattering Compensation:** Software compensation applied to optical gas sensors to correct readings in high-density coal dust environments.

---

## 🛠️ Installation & Execution

### Prerequisites

* **Python 3.10+**
* `pip` package manager

### 1. Environment Setup

```bash
# Clone the repository
git clone [https://github.com/moinkhanCreates/mine-x-gcs-dashboard.git](https://github.com/moinkhanCreates/mine-x-gcs-dashboard.git)
cd mine-x-gcs-dashboard

# Create and activate Python virtual environment
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate

```

### 2. Install Dependencies

```bash
pip install -r requirements.txt

```

### 3. Launch Telemetry Console

```bash
streamlit run app.py

```

The GCS dashboard will open automatically at `http://localhost:8501`.

---

## 📂 Project Structure

```text
mine-x-gcs-dashboard/
│
├── app.py                  # Streamlit Enterprise GCS UI dashboard
├── mine_analytics.py       # Mathematical engine for atmospheric mine physics
├── requirements.txt        # System dependencies
└── README.md               # Technical documentation

```

---

## ⚖️ Standards & Compliance References

* **DGMS (Directorate General of Mines Safety, India):** Guidelines for Flameproof Electrical Apparatus (Ex-d) in gassy coal mines.
* **IS/IEC 60079-1:** Explosive atmospheres - Equipment protection by flameproof enclosures "d".
* **US Bureau of Mines (USBM) Bulletin 627:** Flammability characteristics of combustible gases and vapors.

---
