"""
Deduction Calculator for PND 94 (ภ.ง.ด. 94).
คำนวณค่าลดหย่อนสำหรับการยื่นครึ่งปี

Business rules:
- ค่าลดหย่อนส่วนใหญ่หาร 2 จากเต็มปี
- ประกันชีวิต: กรณีพิเศษ 2 tier
  - ส่วนแรก 10,000: หักได้ครึ่ง (max 5,000)
  - ส่วนเกิน 10,000: หักได้อีกไม่เกิน 90,000
  - รวมชีวิต + สุขภาพ cap 95,000
- กลุ่มเกษียณ: เฉพาะ บำนาญ + RMF + กอช. (ไม่มี PVD, กบข.)
  - cap รวม 500,000 (ไม่หาร)
- Thai ESG: แยกวง
- บริจาค: หาร 2 (cap 5% แทน 10%)
"""

from typing import Optional

from models.deductions import (
    DeductionEntry, DeductionType, DeductionLineItem,
    DeductionResult, RETIREMENT_GROUP_TYPES_PND94,
)
from config.tax_rates_2569_pnd94 import (
    PERSONAL_ALLOWANCE, SPOUSE_ALLOWANCE,
    CHILD_ALLOWANCE, CHILD_ALLOWANCE_BORN_2018_PLUS,
    PREGNANCY_ALLOWANCE_CAP, PARENT_ALLOWANCE, DISABLED_PERSON_ALLOWANCE,
    # Life insurance — special 2-tier
    LIFE_INSURANCE_FIRST_TIER, LIFE_INSURANCE_FIRST_TIER_RATE,
    LIFE_INSURANCE_FIRST_TIER_CAP, LIFE_INSURANCE_SECOND_TIER_CAP,
    LIFE_PLUS_HEALTH_COMBINED_CAP,
    HEALTH_INSURANCE_CAP,
    PARENT_HEALTH_INSURANCE_CAP,
    # Retirement group
    LIFE_INSURANCE_ANNUITY_RATE, LIFE_INSURANCE_ANNUITY_CAP,
    RMF_RATE, RMF_CAP,
    NATIONAL_SAVINGS_FUND_CAP, RETIREMENT_GROUP_CAP,
    # ESG
    THAI_ESG_RATE, THAI_ESG_CAP,
    THAI_ESGX_CAP,
    # Social security
    SOCIAL_SECURITY_CAP,
    # Stimulus
    HOME_LOAN_INTEREST_CAP, SOLAR_ROOFTOP_CAP,
    VISUAL_ART_CAP, SOCIAL_ENTERPRISE_CAP,
    ENERGY_SAVING_CAP, CCTV_CAP,
    # Donation
    DONATION_DOUBLE_RATE, DONATION_DOUBLE_CAP_RATE,
    DONATION_GENERAL_CAP_RATE, POLITICAL_PARTY_DONATION_CAP,
)


class DeductionCalculatorPND94:
    """คำนวณค่าลดหย่อนสำหรับ ภ.ง.ด. 94"""

    def calculate(
        self,
        entries: list[DeductionEntry],
        assessable_income: float,
        income_after_expenses: float,
    ) -> DeductionResult:
        result = DeductionResult()

        entry_map: dict[DeductionType, DeductionEntry] = {}
        for e in entries:
            entry_map[e.deduction_type] = e

        # --- Phase 1: Individual caps (non-donation) ---
        non_donation_items: list[DeductionLineItem] = []

        for entry in entries:
            if entry.deduction_type in (
                DeductionType.DONATION_DOUBLE,
                DeductionType.DONATION_GENERAL,
            ):
                continue

            item = self._apply_individual_cap(entry, assessable_income)
            non_donation_items.append(item)

        # --- Phase 2: Group caps ---

        # 2a: ประกันชีวิต + ประกันสุขภาพ รวมไม่เกิน 95,000
        self._apply_life_health_combined_cap(non_donation_items)

        # 2b: กลุ่มเกษียณ รวมไม่เกิน 500,000
        self._apply_retirement_group_cap(non_donation_items)

        for item in non_donation_items:
            result.line_items.append(item)

        # --- Phase 3: Donations ---
        total_non_donation = sum(item.final_amount for item in non_donation_items)
        base_for_donation = income_after_expenses - total_non_donation

        # 3a: Political party donation
        political_entry = entry_map.get(DeductionType.POLITICAL_PARTY)
        if political_entry:
            allowed = min(political_entry.actual_amount, POLITICAL_PARTY_DONATION_CAP)
            result.line_items.append(DeductionLineItem(
                deduction_type=DeductionType.POLITICAL_PARTY,
                claimed_amount=political_entry.actual_amount,
                allowed_amount=allowed,
                final_amount=allowed,
                cap_applied=f"max {POLITICAL_PARTY_DONATION_CAP:,.0f}",
            ))
            base_for_donation -= allowed

        # 3b: บริจาค 2 เท่า — cap 5% (halved from 10%)
        donation_double_entry = entry_map.get(DeductionType.DONATION_DOUBLE)
        donation_double_amount = 0.0
        if donation_double_entry:
            doubled = donation_double_entry.actual_amount * DONATION_DOUBLE_RATE
            cap_pct = max(base_for_donation * DONATION_DOUBLE_CAP_RATE, 0)
            allowed = min(doubled, cap_pct)
            donation_double_amount = allowed
            result.line_items.append(DeductionLineItem(
                deduction_type=DeductionType.DONATION_DOUBLE,
                claimed_amount=donation_double_entry.actual_amount,
                allowed_amount=doubled,
                final_amount=allowed,
                cap_applied=f"2x actual, max 5% of {base_for_donation:,.0f}",
                notes="PND94: cap halved to 5%",
            ))

        # 3c: บริจาคทั่วไป — cap 5% of remaining base
        donation_general_entry = entry_map.get(DeductionType.DONATION_GENERAL)
        if donation_general_entry:
            remaining_base = base_for_donation - donation_double_amount
            cap_pct = max(remaining_base * DONATION_GENERAL_CAP_RATE, 0)
            allowed = min(donation_general_entry.actual_amount, cap_pct)
            result.line_items.append(DeductionLineItem(
                deduction_type=DeductionType.DONATION_GENERAL,
                claimed_amount=donation_general_entry.actual_amount,
                allowed_amount=donation_general_entry.actual_amount,
                final_amount=allowed,
                cap_applied=f"max 5% of {remaining_base:,.0f} (after donation double)",
                notes="PND94: cap halved to 5%",
            ))

        return result

    # -------------------------------------------------------------------------
    # Individual cap logic
    # -------------------------------------------------------------------------

    def _apply_individual_cap(
        self, entry: DeductionEntry, assessable_income: float
    ) -> DeductionLineItem:
        dt = entry.deduction_type
        amount = entry.actual_amount
        count = entry.count

        cap: Optional[float] = None
        claimed = amount
        notes = None

        # Group A: ส่วนตัวและครอบครัว (halved)
        if dt == DeductionType.PERSONAL:
            claimed = PERSONAL_ALLOWANCE
            cap = PERSONAL_ALLOWANCE
        elif dt == DeductionType.SPOUSE:
            claimed = SPOUSE_ALLOWANCE
            cap = SPOUSE_ALLOWANCE
        elif dt == DeductionType.CHILD:
            claimed = CHILD_ALLOWANCE * count
            cap = CHILD_ALLOWANCE * count
        elif dt == DeductionType.CHILD_BORN_2018_PLUS:
            claimed = CHILD_ALLOWANCE_BORN_2018_PLUS * count
            cap = CHILD_ALLOWANCE_BORN_2018_PLUS * count
        elif dt == DeductionType.PREGNANCY:
            claimed = min(amount, PREGNANCY_ALLOWANCE_CAP * count)
            cap = PREGNANCY_ALLOWANCE_CAP * count
        elif dt == DeductionType.PARENT:
            claimed = PARENT_ALLOWANCE * count
            cap = PARENT_ALLOWANCE * count
        elif dt == DeductionType.DISABLED_PERSON:
            claimed = DISABLED_PERSON_ALLOWANCE * count
            cap = DISABLED_PERSON_ALLOWANCE * count

        # Group B: ประกันชีวิต — special 2-tier logic
        elif dt == DeductionType.LIFE_INSURANCE:
            claimed, cap, notes = self._calc_life_insurance(amount)

        elif dt == DeductionType.HEALTH_INSURANCE:
            cap = HEALTH_INSURANCE_CAP
            claimed = min(amount, cap)

        elif dt == DeductionType.PARENT_HEALTH_INSURANCE:
            cap = PARENT_HEALTH_INSURANCE_CAP
            claimed = min(amount, cap)

        # Retirement group members (PND94: only annuity, RMF, NSF)
        elif dt == DeductionType.LIFE_INSURANCE_ANNUITY:
            pct_cap = assessable_income * LIFE_INSURANCE_ANNUITY_RATE
            cap = min(pct_cap, LIFE_INSURANCE_ANNUITY_CAP)
            claimed = min(amount, cap)
            notes = f"15% of income = {pct_cap:,.0f}, hard cap = {LIFE_INSURANCE_ANNUITY_CAP:,}"

        elif dt == DeductionType.RMF:
            pct_cap = assessable_income * RMF_RATE
            cap = min(pct_cap, RMF_CAP)
            claimed = min(amount, cap)
            notes = f"30% of income = {pct_cap:,.0f}, hard cap = {RMF_CAP:,}"

        elif dt == DeductionType.NATIONAL_SAVINGS_FUND:
            cap = NATIONAL_SAVINGS_FUND_CAP
            claimed = min(amount, cap)

        # Thai ESG — separate from retirement
        elif dt == DeductionType.THAI_ESG:
            pct_cap = assessable_income * THAI_ESG_RATE
            cap = min(pct_cap, THAI_ESG_CAP)
            claimed = min(amount, cap)
            notes = f"30% of income = {pct_cap:,.0f}, hard cap = {THAI_ESG_CAP:,}"

        elif dt == DeductionType.THAI_ESGX:
            cap = THAI_ESGX_CAP
            claimed = min(amount, cap)

        elif dt == DeductionType.SOCIAL_SECURITY:
            cap = SOCIAL_SECURITY_CAP
            claimed = min(amount, cap)

        # Group C: กระตุ้นเศรษฐกิจ (halved)
        elif dt == DeductionType.HOME_LOAN_INTEREST:
            cap = HOME_LOAN_INTEREST_CAP
            claimed = min(amount, cap)

        elif dt == DeductionType.SOLAR_ROOFTOP:
            cap = SOLAR_ROOFTOP_CAP
            claimed = min(amount, cap)

        elif dt == DeductionType.VISUAL_ART:
            cap = VISUAL_ART_CAP
            claimed = min(amount, cap)

        elif dt == DeductionType.SOCIAL_ENTERPRISE:
            cap = SOCIAL_ENTERPRISE_CAP
            claimed = min(amount, cap)

        elif dt == DeductionType.ENERGY_SAVING:
            # No cap — ตามจริง
            cap = ENERGY_SAVING_CAP  # None
            claimed = amount

        elif dt == DeductionType.CCTV:
            # No cap — ตามจริง
            cap = CCTV_CAP  # None
            claimed = amount

        # Political party handled in Phase 3
        elif dt == DeductionType.POLITICAL_PARTY:
            cap = POLITICAL_PARTY_DONATION_CAP
            claimed = min(amount, cap)

        else:
            claimed = amount

        # Determine if this is a fixed-amount type (not user-input)
        fixed_types = {
            DeductionType.PERSONAL, DeductionType.SPOUSE,
            DeductionType.CHILD, DeductionType.CHILD_BORN_2018_PLUS,
            DeductionType.PARENT, DeductionType.DISABLED_PERSON,
        }

        return DeductionLineItem(
            deduction_type=dt,
            claimed_amount=claimed if dt in fixed_types else amount,
            allowed_amount=claimed,
            final_amount=claimed,
            cap_applied=f"max {cap:,.0f}" if cap is not None else None,
            notes=notes,
        )

    def _calc_life_insurance(self, amount: float) -> tuple[float, float, str]:
        """
        ประกันชีวิต PND94 — กรณีพิเศษ 2 tier:
        - ส่วนแรก 10,000: หักได้ครึ่ง → max 5,000
        - ส่วนเกิน 10,000: หักได้อีกไม่เกิน 90,000
        - รวม max 95,000 (ก่อนรวมสุขภาพ)
        """
        # Tier 1: first 10,000 → halved
        tier1_input = min(amount, LIFE_INSURANCE_FIRST_TIER)
        tier1_deduction = tier1_input * LIFE_INSURANCE_FIRST_TIER_RATE
        tier1_deduction = min(tier1_deduction, LIFE_INSURANCE_FIRST_TIER_CAP)

        # Tier 2: amount beyond 10,000 → up to 90,000
        tier2_input = max(amount - LIFE_INSURANCE_FIRST_TIER, 0)
        tier2_deduction = min(tier2_input, LIFE_INSURANCE_SECOND_TIER_CAP)

        total = tier1_deduction + tier2_deduction

        # The individual cap for life insurance alone (before combined with health)
        # is the sum of the two tiers = max 95,000
        effective_cap = LIFE_INSURANCE_FIRST_TIER_CAP + LIFE_INSURANCE_SECOND_TIER_CAP

        notes = (
            f"PND94 2-tier: paid {amount:,.0f} → "
            f"tier1 {tier1_input:,.0f}×50%={tier1_deduction:,.0f}, "
            f"tier2 {tier2_input:,.0f}→{tier2_deduction:,.0f}"
        )

        return total, effective_cap, notes

    # -------------------------------------------------------------------------
    # Group cap logic
    # -------------------------------------------------------------------------

    def _apply_life_health_combined_cap(
        self, items: list[DeductionLineItem]
    ) -> None:
        """ประกันชีวิต + ประกันสุขภาพ รวมไม่เกิน 95,000 (PND94)"""
        life = None
        health = None
        for item in items:
            if item.deduction_type == DeductionType.LIFE_INSURANCE:
                life = item
            elif item.deduction_type == DeductionType.HEALTH_INSURANCE:
                health = item

        if life is None and health is None:
            return

        life_amount = life.final_amount if life else 0
        health_amount = health.final_amount if health else 0
        combined = life_amount + health_amount

        if combined > LIFE_PLUS_HEALTH_COMBINED_CAP:
            ratio = LIFE_PLUS_HEALTH_COMBINED_CAP / combined
            if life:
                life.final_amount = life.final_amount * ratio
                life.cap_applied = f"combined life+health cap {LIFE_PLUS_HEALTH_COMBINED_CAP:,}"
            if health:
                health.final_amount = health.final_amount * ratio
                health.cap_applied = f"combined life+health cap {LIFE_PLUS_HEALTH_COMBINED_CAP:,}"

    def _apply_retirement_group_cap(
        self, items: list[DeductionLineItem]
    ) -> None:
        """กลุ่มเกษียณ PND94: เฉพาะ บำนาญ + RMF + กอช. รวมไม่เกิน 500,000"""
        retirement_items = [
            item for item in items
            if item.deduction_type in RETIREMENT_GROUP_TYPES_PND94
        ]

        if not retirement_items:
            return

        total = sum(item.final_amount for item in retirement_items)

        if total > RETIREMENT_GROUP_CAP:
            ratio = RETIREMENT_GROUP_CAP / total
            for item in retirement_items:
                item.final_amount = item.final_amount * ratio
                item.notes = (item.notes or "") + f" | reduced by retirement group cap {RETIREMENT_GROUP_CAP:,}"
