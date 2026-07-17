"""
Deduction Calculator.
คำนวณค่าลดหย่อนพร้อม cap เฉพาะตัว, cap รวมกลุ่ม, และ logic บริจาค

Business rules:
- ประกันชีวิต + ประกันสุขภาพ รวมไม่เกิน 100,000
- กลุ่มเกษียณ: cap เฉพาะตัวก่อน → cap รวม 500,000
- Thai ESG: แยกวงจากกลุ่มเกษียณ
- บริจาค 2 เท่า: คิดก่อน → ไม่เกิน 10% ของเงินได้หลังหักลดหย่อนอื่น
- บริจาคทั่วไป: คิดทีหลัง → ไม่เกิน 10% ของฐานที่เหลือหลังหัก 2 เท่า
"""

from dataclasses import dataclass
from typing import Optional

from models.deductions import (
    DeductionEntry, DeductionType, DeductionLineItem,
    DeductionResult, RETIREMENT_GROUP_TYPES,
)
from config.tax_rates_2568 import (
    PERSONAL_ALLOWANCE, SPOUSE_ALLOWANCE,
    CHILD_ALLOWANCE, CHILD_ALLOWANCE_BORN_2018_PLUS,
    PREGNANCY_ALLOWANCE_CAP, PARENT_ALLOWANCE, DISABLED_PERSON_ALLOWANCE,
    LIFE_INSURANCE_CAP, HEALTH_INSURANCE_CAP, LIFE_PLUS_HEALTH_COMBINED_CAP,
    PARENT_HEALTH_INSURANCE_CAP,
    LIFE_INSURANCE_ANNUITY_RATE, LIFE_INSURANCE_ANNUITY_CAP,
    PVD_RATE, PVD_CAP,
    NATIONAL_SAVINGS_FUND_CAP, GPF_CAP, PRIVATE_TEACHER_AID_FUND_CAP,
    RMF_RATE, RMF_CAP, RETIREMENT_GROUP_CAP,
    THAI_ESG_RATE, THAI_ESG_CAP,
    SOCIAL_SECURITY_CAP,
    EASY_E_RECEIPT_CAP, HOME_LOAN_INTEREST_CAP,
    NEW_HOME_CONSTRUCTION_CAP, VISUAL_ART_CAP,
    DONATION_DOUBLE_RATE, DONATION_DOUBLE_CAP_RATE,
    DONATION_GENERAL_CAP_RATE, POLITICAL_PARTY_DONATION_CAP,
)


class DeductionCalculator:
    """คำนวณค่าลดหย่อนทั้งหมด"""

    def calculate(
        self,
        entries: list[DeductionEntry],
        assessable_income: float,
        income_after_expenses: float,
    ) -> DeductionResult:
        """
        Args:
            entries: รายการค่าลดหย่อนทั้งหมด
            assessable_income: เงินได้พึงประเมิน (สำหรับคำนวณ % cap)
            income_after_expenses: เงินได้หลังหักค่าใช้จ่าย (สำหรับ cap บริจาค)
        """
        result = DeductionResult()

        # Build lookup: deduction_type → entry
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
                continue  # Handle in Phase 3

            item = self._apply_individual_cap(entry, assessable_income)
            non_donation_items.append(item)

        # --- Phase 2: Group caps ---

        # 2a: ประกันชีวิต + ประกันสุขภาพ รวมไม่เกิน 100,000
        self._apply_life_health_combined_cap(non_donation_items)

        # 2b: กลุ่มเกษียณ รวมไม่เกิน 500,000
        self._apply_retirement_group_cap(non_donation_items)

        # Add non-donation items to result
        for item in non_donation_items:
            result.line_items.append(item)

        # --- Phase 3: Donations (sequential, not parallel) ---
        total_non_donation = sum(item.final_amount for item in non_donation_items)
        base_for_donation = income_after_expenses - total_non_donation

        # 3a: Political party donation (fixed cap, not % based)
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

        # 3b: บริจาค 2 เท่า (คิดก่อน)
        donation_double_entry = entry_map.get(DeductionType.DONATION_DOUBLE)
        donation_double_amount = 0.0
        if donation_double_entry:
            doubled = donation_double_entry.actual_amount * DONATION_DOUBLE_RATE
            cap_10pct = max(base_for_donation * DONATION_DOUBLE_CAP_RATE, 0)
            allowed = min(doubled, cap_10pct)
            donation_double_amount = allowed
            result.line_items.append(DeductionLineItem(
                deduction_type=DeductionType.DONATION_DOUBLE,
                claimed_amount=donation_double_entry.actual_amount,
                allowed_amount=doubled,
                final_amount=allowed,
                cap_applied=f"2x actual, max 10% of {base_for_donation:,.0f}",
                notes=f"Calculated before general donation",
            ))

        # 3c: บริจาคทั่วไป (คิดจากฐานที่เหลือหลังหัก 2 เท่า)
        donation_general_entry = entry_map.get(DeductionType.DONATION_GENERAL)
        if donation_general_entry:
            remaining_base = base_for_donation - donation_double_amount
            cap_10pct = max(remaining_base * DONATION_GENERAL_CAP_RATE, 0)
            allowed = min(donation_general_entry.actual_amount, cap_10pct)
            result.line_items.append(DeductionLineItem(
                deduction_type=DeductionType.DONATION_GENERAL,
                claimed_amount=donation_general_entry.actual_amount,
                allowed_amount=donation_general_entry.actual_amount,
                final_amount=allowed,
                cap_applied=f"max 10% of {remaining_base:,.0f} (after donation double)",
                notes="Calculated after donation double",
            ))

        return result

    # -------------------------------------------------------------------------
    # Individual cap logic
    # -------------------------------------------------------------------------

    def _apply_individual_cap(
        self, entry: DeductionEntry, assessable_income: float
    ) -> DeductionLineItem:
        """Apply individual cap per deduction type."""

        dt = entry.deduction_type
        amount = entry.actual_amount
        count = entry.count

        cap: Optional[float] = None
        claimed = amount
        notes = None

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

        elif dt == DeductionType.LIFE_INSURANCE:
            cap = LIFE_INSURANCE_CAP
            claimed = min(amount, cap)
        elif dt == DeductionType.HEALTH_INSURANCE:
            cap = HEALTH_INSURANCE_CAP
            claimed = min(amount, cap)
        elif dt == DeductionType.PARENT_HEALTH_INSURANCE:
            cap = PARENT_HEALTH_INSURANCE_CAP
            claimed = min(amount, cap)

        elif dt == DeductionType.LIFE_INSURANCE_ANNUITY:
            pct_cap = assessable_income * LIFE_INSURANCE_ANNUITY_RATE
            cap = min(pct_cap, LIFE_INSURANCE_ANNUITY_CAP)
            claimed = min(amount, cap)
            notes = f"15% of income = {pct_cap:,.0f}, hard cap = {LIFE_INSURANCE_ANNUITY_CAP:,}"
        elif dt == DeductionType.PVD:
            pct_cap = assessable_income * PVD_RATE
            cap = min(pct_cap, PVD_CAP)
            claimed = min(amount, cap)
            notes = f"15% of salary = {pct_cap:,.0f}, hard cap = {PVD_CAP:,}"
        elif dt == DeductionType.NATIONAL_SAVINGS_FUND:
            cap = NATIONAL_SAVINGS_FUND_CAP
            claimed = min(amount, cap)
        elif dt == DeductionType.GPF:
            cap = GPF_CAP
            claimed = min(amount, cap)
        elif dt == DeductionType.PRIVATE_TEACHER_FUND:
            cap = PRIVATE_TEACHER_AID_FUND_CAP
            claimed = min(amount, cap)
        elif dt == DeductionType.RMF:
            pct_cap = assessable_income * RMF_RATE
            cap = min(pct_cap, RMF_CAP)
            claimed = min(amount, cap)
            notes = f"30% of income = {pct_cap:,.0f}, hard cap = {RMF_CAP:,}"

        elif dt == DeductionType.THAI_ESG:
            pct_cap = assessable_income * THAI_ESG_RATE
            cap = min(pct_cap, THAI_ESG_CAP)
            claimed = min(amount, cap)
            notes = f"30% of income = {pct_cap:,.0f}, hard cap = {THAI_ESG_CAP:,}"

        elif dt == DeductionType.SOCIAL_SECURITY:
            cap = SOCIAL_SECURITY_CAP
            claimed = min(amount, cap)

        elif dt == DeductionType.EASY_E_RECEIPT:
            cap = EASY_E_RECEIPT_CAP
            claimed = min(amount, cap)
        elif dt == DeductionType.HOME_LOAN_INTEREST:
            cap = HOME_LOAN_INTEREST_CAP
            claimed = min(amount, cap)
        elif dt == DeductionType.NEW_HOME_CONSTRUCTION:
            cap = NEW_HOME_CONSTRUCTION_CAP
            claimed = min(amount, cap)
        elif dt == DeductionType.VISUAL_ART:
            cap = VISUAL_ART_CAP
            claimed = min(amount, cap)

        elif dt == DeductionType.POLITICAL_PARTY:
            cap = POLITICAL_PARTY_DONATION_CAP
            claimed = min(amount, cap)

        else:
            claimed = amount

        return DeductionLineItem(
            deduction_type=dt,
            claimed_amount=amount if dt not in (
                DeductionType.PERSONAL, DeductionType.SPOUSE,
                DeductionType.CHILD, DeductionType.CHILD_BORN_2018_PLUS,
                DeductionType.PARENT, DeductionType.DISABLED_PERSON,
            ) else claimed,
            allowed_amount=claimed,
            final_amount=claimed,  # May be reduced by group cap later
            cap_applied=f"max {cap:,.0f}" if cap else None,
            notes=notes,
        )

    # -------------------------------------------------------------------------
    # Group cap logic
    # -------------------------------------------------------------------------

    def _apply_life_health_combined_cap(
        self, items: list[DeductionLineItem]
    ) -> None:
        """ประกันชีวิต + ประกันสุขภาพ รวมไม่เกิน 100,000"""
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
            # Reduce proportionally
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
        """กลุ่มเกษียณ รวมไม่เกิน 500,000"""
        retirement_items = [
            item for item in items
            if item.deduction_type in RETIREMENT_GROUP_TYPES
        ]

        if not retirement_items:
            return

        total = sum(item.final_amount for item in retirement_items)

        if total > RETIREMENT_GROUP_CAP:
            # Reduce proportionally
            ratio = RETIREMENT_GROUP_CAP / total
            for item in retirement_items:
                item.final_amount = item.final_amount * ratio
                item.notes = (item.notes or "") + f" | reduced by retirement group cap {RETIREMENT_GROUP_CAP:,}"
