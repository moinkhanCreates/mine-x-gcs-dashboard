"""
mine_analytics.py
==================
Underground Mine Atmospheric & Fire-Risk Analysis Engine.

Implements the standard gas-ratio indices used in coal-mine spontaneous
combustion monitoring, general industrial-hygiene classification bands for
oxygen/methane/carbon-monoxide, and a simplified explosibility check based
on the Coward Flammability Triangle for methane / oxygen / inert mixtures.

Fire-risk indices implemented (all derived from oxygen deficiency, dO2):
    - Graham's Ratio            CO  / dO2   -- primary heating index
    - Young's Ratio              CO2 / dO2   -- supplementary heating index
    - Jones & Trickett Ratio     (CO2 + 0.75*CO - 0.25*H2) / dO2
    - Oxides of Carbon Ratio     CO  / CO2

These ratios are standard references in mine-fire literature for detecting
the onset and progression of spontaneous heating in ventilated workings.
Graham's Ratio is the most widely used because it is the easiest to
interpret in isolation; the others are supplementary corroborating
evidence and, outside of Graham's Ratio, do not have universally agreed
numeric alarm bands across coal ranks -- they are reported as computed
values for a qualified reader, not auto-classified into severity tiers.

The Coward Triangle evaluation below is a linearised approximation for
dashboard/demonstration purposes. It is NOT a substitute for a certified
explosimeter reading or a full ternary-diagram lookup in a real mine.

This module has no external dependencies beyond the Python standard library.
"""

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #

class HazardLevel(Enum):
    """Composite hazard level surfaced on the operator console."""
    NOMINAL = "NOMINAL"
    CAUTION = "CAUTION"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class OxygenState(Enum):
    NORMAL = "NORMAL"
    ACCEPTABLE = "ACCEPTABLE"
    DEFICIENT = "OXYGEN DEFICIENT"
    DANGEROUS = "IMMEDIATELY DANGEROUS"


class MethaneState(Enum):
    BACKGROUND = "BACKGROUND"
    ELEVATED = "ELEVATED, BELOW LEL"
    EXPLOSIVE_RANGE = "WITHIN EXPLOSIVE RANGE"
    ABOVE_UEL = "ABOVE UEL, FUEL-RICH"


class CoExposureState(Enum):
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    SEVERE = "SEVERE"
    IDLH = "IMMEDIATELY DANGEROUS TO LIFE"


# --------------------------------------------------------------------------- #
# Result container
# --------------------------------------------------------------------------- #

@dataclass
class AtmosphericStatus:
    # Raw inputs, echoed back for logging / downstream telemetry
    ch4_pct: float
    o2_pct: float
    co_ppm: float
    co2_pct: float
    h2_ppm: float
    n2_pct: float

    # Derived classification
    o2_deficiency_pct: float
    oxygen_state: OxygenState
    methane_state: MethaneState
    co_exposure_state: CoExposureState

    # Fire-risk indices
    grahams_ratio: float
    grahams_status: str
    youngs_ratio: Optional[float]
    jones_trickett_ratio: Optional[float]
    co_co2_ratio: Optional[float]

    # Explosibility
    coward_status: str

    # Trend (percent CH4 per minute, based on rolling history)
    ch4_trend_pct_per_min: Optional[float]

    # Composite output
    hazard_level: HazardLevel
    is_hazard: bool
    advisory: str
    summary: str


# --------------------------------------------------------------------------- #
# Analyzer
# --------------------------------------------------------------------------- #

class MineAtmosphericAnalyzer:
    """
    Stateful atmospheric analysis engine for a single rover / borehole gas
    sensing node. Retains a short rolling history of methane readings to
    estimate a first-order concentration trend across successive samples.
    """

    #: Ratio of O2 to N2 in normal, unburned atmospheric air (20.93 / 79.07)
    AIR_O2_N2_RATIO = 0.2649

    #: Methane lower / upper explosive limits, percent by volume
    CH4_LEL = 5.0
    CH4_UEL = 15.0

    def __init__(self, history_window: int = 40, sample_interval_s: float = 2.0):
        self._ch4_history: deque = deque(maxlen=history_window)
        self._sample_interval_s = sample_interval_s

    # ---- classification helpers ------------------------------------------------ #

    def classify_oxygen(self, o2_pct: float) -> OxygenState:
        """OSHA-style general oxygen-deficiency classification (vol %)."""
        if o2_pct >= 20.0:
            return OxygenState.NORMAL
        if o2_pct >= 19.5:
            return OxygenState.ACCEPTABLE
        if o2_pct >= 16.0:
            return OxygenState.DEFICIENT
        return OxygenState.DANGEROUS

    def classify_methane(self, ch4_pct: float) -> MethaneState:
        """Classification relative to the methane LEL/UEL band."""
        if ch4_pct < 1.0:
            return MethaneState.BACKGROUND
        if ch4_pct < self.CH4_LEL:
            return MethaneState.ELEVATED
        if ch4_pct <= self.CH4_UEL:
            return MethaneState.EXPLOSIVE_RANGE
        return MethaneState.ABOVE_UEL

    def classify_co_exposure(self, co_ppm: float) -> CoExposureState:
        """General OSHA/NIOSH-referenced CO exposure banding."""
        if co_ppm < 25:
            return CoExposureState.NORMAL
        if co_ppm < 50:
            return CoExposureState.ELEVATED
        if co_ppm < 200:
            return CoExposureState.HIGH
        if co_ppm < 1200:
            return CoExposureState.SEVERE
        return CoExposureState.IDLH

    # ---- fire-ratio indices ------------------------------------------------- #

    def _oxygen_deficiency(self, o2_pct: float, n2_pct: float) -> float:
        """
        Oxygen deficiency (dO2), percent by volume: the gap between the O2
        level that *should* accompany the measured N2 in unburned air, and
        the O2 level actually measured. A positive value indicates oxygen
        consumption consistent with combustion or oxidation.
        """
        expected_o2 = self.AIR_O2_N2_RATIO * n2_pct
        return expected_o2 - o2_pct

    def calculate_grahams_ratio(self, co_ppm: float, o2_deficit_pct: float):
        """
        Graham's Ratio (Index of Carbon Monoxide): CO / dO2, expressed as a
        percentage. The most widely used early-warning index for
        spontaneous heating in ventilated coal-mine workings.
        """
        if o2_deficit_pct <= 0.05:
            return 0.0, "NORMAL_BACKGROUND"

        co_pct = co_ppm / 10_000.0
        gr = (co_pct / o2_deficit_pct) * 100.0

        if gr < 0.4:
            status = "NORMAL_BACKGROUND"
        elif gr < 0.5:
            status = "POSSIBLE_HEATING"
        elif gr < 1.0:
            status = "SPONTANEOUS_HEATING_CONFIRMED"
        elif gr < 2.0:
            status = "SERIOUS_ADVANCED_HEATING"
        elif gr < 3.0:
            status = "CRITICAL_HEATING_IMMINENT"
        else:
            status = "ACTIVE_MINE_FIRE_CONFIRMED"

        return round(gr, 3), status

    def calculate_youngs_ratio(self, co2_pct: float, o2_deficit_pct: float) -> Optional[float]:
        """Young's Ratio: CO2 / dO2. Supplementary corroborating index."""
        if o2_deficit_pct <= 0.05:
            return None
        return round(co2_pct / o2_deficit_pct, 3)

    def calculate_jones_trickett_ratio(
        self, co2_pct: float, co_ppm: float, h2_ppm: float, o2_deficit_pct: float
    ) -> Optional[float]:
        """Jones & Trickett Ratio: (CO2 + 0.75*CO - 0.25*H2) / dO2 (all in vol %)."""
        if o2_deficit_pct <= 0.05:
            return None
        co_pct = co_ppm / 10_000.0
        h2_pct = h2_ppm / 10_000.0
        numerator = co2_pct + (0.75 * co_pct) - (0.25 * h2_pct)
        return round(numerator / o2_deficit_pct, 3)

    def calculate_co_co2_ratio(self, co_ppm: float, co2_pct: float) -> Optional[float]:
        """Oxides of Carbon Ratio: CO / CO2, both expressed in ppm."""
        co2_ppm = co2_pct * 10_000.0
        if co2_ppm <= 1.0:
            return None
        return round(co_ppm / co2_ppm, 4)

    # ---- explosibility (Coward triangle) ------------------------------------- #

    def evaluate_coward_triangle(self, ch4: float, o2: float) -> str:
        """
        Simplified, linearised approximation of the Coward Explosibility
        Triangle for a methane / oxygen / inert-gas mixture. Intended for
        dashboard demonstration only -- not a certified explosimeter
        replacement.
        """
        max_o2_possible = 20.93 * (1.0 - (ch4 / 100.0))
        if o2 > max_o2_possible + 0.5:
            return "IMPOSSIBLE_MIXTURE (Exceeds Ambient Air O2 Ratio)"

        lower_boundary_ch4 = -0.1157 * (o2 - 12.1) + 5.9
        upper_boundary_ch4 = 1.5993 * (o2 - 12.1) + 5.9
        nose_line_ch4 = (5.9 / 12.1) * o2

        if o2 >= 12.1:
            if lower_boundary_ch4 <= ch4 <= upper_boundary_ch4:
                return "EXPLOSIVE MIXTURE DETECTED"
            elif ch4 > upper_boundary_ch4:
                return "POTENTIALLY EXPLOSIVE (Fuel-Rich)"
            elif ch4 < lower_boundary_ch4 and ch4 >= 5.0:
                return "POTENTIALLY EXPLOSIVE (Near LEL)"
            else:
                return "NON_EXPLOSIVE (Methane Below LEL)"
        else:
            if ch4 >= nose_line_ch4:
                return "POTENTIALLY EXPLOSIVE (Sub-Critical O2)"
            return "INCAPABLE OF EXPLODING (Inert Zone)"

    # ---- trend ---------------------------------------------------------------- #

    def _update_trend(self, ch4_pct: float) -> Optional[float]:
        """Rolling first-order rate of change of CH4, in vol % per minute."""
        self._ch4_history.append(ch4_pct)
        if len(self._ch4_history) < 2:
            return None
        delta = self._ch4_history[-1] - self._ch4_history[0]
        elapsed_min = (len(self._ch4_history) - 1) * self._sample_interval_s / 60.0
        if elapsed_min <= 0:
            return None
        return round(delta / elapsed_min, 4)

    # ---- composite hazard ------------------------------------------------------ #

    def _composite_hazard(
        self,
        coward_status: str,
        grahams_status: str,
        oxygen_state: OxygenState,
        co_exposure_state: CoExposureState,
    ) -> HazardLevel:
        if (
            "EXPLOSIVE MIXTURE DETECTED" in coward_status
            or "ACTIVE_MINE_FIRE" in grahams_status
            or oxygen_state == OxygenState.DANGEROUS
            or co_exposure_state == CoExposureState.IDLH
        ):
            return HazardLevel.CRITICAL

        if (
            "POTENTIALLY EXPLOSIVE" in coward_status
            or grahams_status in ("SERIOUS_ADVANCED_HEATING", "CRITICAL_HEATING_IMMINENT")
            or oxygen_state == OxygenState.DEFICIENT
            or co_exposure_state == CoExposureState.SEVERE
        ):
            return HazardLevel.WARNING

        if (
            grahams_status in ("POSSIBLE_HEATING", "SPONTANEOUS_HEATING_CONFIRMED")
            or oxygen_state == OxygenState.ACCEPTABLE
            or co_exposure_state in (CoExposureState.ELEVATED, CoExposureState.HIGH)
        ):
            return HazardLevel.CAUTION

        return HazardLevel.NOMINAL

    def _advisory_text(self, hazard_level: HazardLevel) -> str:
        if hazard_level == HazardLevel.CRITICAL:
            return "Withdraw personnel from the sensing zone and notify the mine safety officer immediately."
        if hazard_level == HazardLevel.WARNING:
            return "Increase monitoring frequency and prepare an evacuation contingency for this section."
        if hazard_level == HazardLevel.CAUTION:
            return "Continue monitoring at standard interval; log the trend for the shift report."
        return "No corrective action required. Continue routine monitoring."

    # ---- public entry point ------------------------------------------------- #

    def analyze(
        self,
        ch4_pct: float,
        o2_pct: float,
        co_ppm: float,
        co2_pct: float = 0.03,
        h2_ppm: float = 0.0,
        n2_pct: Optional[float] = None,
    ) -> AtmosphericStatus:

        if n2_pct is None:
            accounted = ch4_pct + o2_pct + co2_pct + (co_ppm / 10_000.0) + (h2_ppm / 10_000.0)
            n2_pct = max(0.0, 100.0 - accounted)

        o2_deficit = self._oxygen_deficiency(o2_pct, n2_pct)

        gr_val, gr_status = self.calculate_grahams_ratio(co_ppm, o2_deficit)
        young_val = self.calculate_youngs_ratio(co2_pct, o2_deficit)
        jt_val = self.calculate_jones_trickett_ratio(co2_pct, co_ppm, h2_ppm, o2_deficit)
        cc_val = self.calculate_co_co2_ratio(co_ppm, co2_pct)

        coward_status = self.evaluate_coward_triangle(ch4_pct, o2_pct)

        oxygen_state = self.classify_oxygen(o2_pct)
        methane_state = self.classify_methane(ch4_pct)
        co_state = self.classify_co_exposure(co_ppm)

        trend = self._update_trend(ch4_pct)

        hazard_level = self._composite_hazard(coward_status, gr_status, oxygen_state, co_state)
        is_hazard = hazard_level in (HazardLevel.WARNING, HazardLevel.CRITICAL)
        advisory = self._advisory_text(hazard_level)

        summary = (
            f"Methane: {coward_status} | Fire Risk: {gr_status} (GR={gr_val}) "
            f"| O2: {oxygen_state.value} | Hazard: {hazard_level.value}"
        )

        return AtmosphericStatus(
            ch4_pct=ch4_pct,
            o2_pct=o2_pct,
            co_ppm=co_ppm,
            co2_pct=co2_pct,
            h2_ppm=h2_ppm,
            n2_pct=round(n2_pct, 3),
            o2_deficiency_pct=round(o2_deficit, 4),
            oxygen_state=oxygen_state,
            methane_state=methane_state,
            co_exposure_state=co_state,
            grahams_ratio=gr_val,
            grahams_status=gr_status,
            youngs_ratio=young_val,
            jones_trickett_ratio=jt_val,
            co_co2_ratio=cc_val,
            coward_status=coward_status,
            ch4_trend_pct_per_min=trend,
            hazard_level=hazard_level,
            is_hazard=is_hazard,
            advisory=advisory,
            summary=summary,
        )