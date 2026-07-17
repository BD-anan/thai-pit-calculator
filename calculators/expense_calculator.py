"""
Expense Deduction Calculator.
คำนวณค่าใช้จ่ายตามประเภทเงินได้

Business rules:
- 40(1) + 40(2) ใช้เพดานค่าใช้จ่ายร่วมกัน 50% ไม่เกิน 100,000 บาท
- 40(3) เหมา 50% ไม่เกิน 100,000 หรือตามจริง
- 40(4) หักค่าใช้จ่ายไม่ได้
- 40(5) เหมาตามประเภททรัพย์สิน หรือตามจริง
- 40(6) เหมาตามวิชาชีพ หรือตามจริง
- 40(7) เหมา 60% หรือตามจริง
- 40(8) เหมา 40%-60% หรือตามจริง
"""

from dataclasses import dataclass, field

from models.income import IncomeType, IncomeEntry, TaxpayerIncome, ExpenseMethod
from config.tax_rates_2568 import (
    EXPENSE_40_1_RATE, EXPENSE_40_2_RATE, EXPENSE_40_1_2_CAP,
    EXPENSE_40_3_RATE, EXPENSE_40_3_CAP,
    EXPENSE_40_4_RATE,
    EXPENSE_40_5_RATES, EXPENSE_40_6_RATES,
    EXPENSE_40_7_RATE, EXPENSE_40_8_RATES,
)


@dataclass
class ExpenseLineItem:
    """ผลลัพธ์การหักค่าใช้จ่ายแต่ละรายการ"""
    income_type: IncomeType
    income_amount: float
    expense_amount: float
    method: str  # "flat_rate" or "actual"
    rate_applied: float | None = None
    cap_applied: float | None = None
    notes: str | None = None


@dataclass
class ExpenseResult:
    """ผลรวมค่าใช้จ่ายทั้งหมด"""
    line_items: list[ExpenseLineItem] = field(default_factory=list)

    @property
    def total_expenses(self) -> float:
        return sum(item.expense_amount for item in self.line_items)

    @property
    def income_after_expenses(self) -> float:
        total_income = sum(item.income_amount for item in self.line_items)
        return total_income - self.total_expenses


class ExpenseCalculator:
    """คำนวณค่าใช้จ่ายตามประเภทเงินได้"""

    def calculate(self, taxpayer_income: TaxpayerIncome) -> ExpenseResult:
        result = ExpenseResult()

        # Step 1: Calculate 40(1) + 40(2) with shared cap
        self._calc_salary_commission(taxpayer_income, result)

        # Step 2: Calculate other income types
        for entry in taxpayer_income.incomes:
            if entry.income_type in (IncomeType.SALARY, IncomeType.COMMISSION):
                continue  # Already handled above
            line_item = self._calc_single_entry(entry)
            result.line_items.append(line_item)

        return result

    def _calc_salary_commission(
        self, taxpayer_income: TaxpayerIncome, result: ExpenseResult
    ) -> None:
        """
        คำนวณค่าใช้จ่าย 40(1) + 40(2) ด้วยเพดานร่วม
        Business rule: หักเหมารวมกัน 50% แต่ไม่เกิน 100,000 บาท
        """
        salary_total = taxpayer_income.total_by_type(IncomeType.SALARY)
        commission_total = taxpayer_income.total_by_type(IncomeType.COMMISSION)
        combined_total = salary_total + commission_total

        if combined_total == 0:
            return

        # Calculate flat-rate expense: 50% of combined, capped at 100,000
        flat_expense = min(combined_total * EXPENSE_40_1_RATE, EXPENSE_40_1_2_CAP)

        # Allocate expense proportionally to each type for reporting
        if salary_total > 0:
            salary_share = (salary_total / combined_total) * flat_expense
            result.line_items.append(ExpenseLineItem(
                income_type=IncomeType.SALARY,
                income_amount=salary_total,
                expense_amount=salary_share,
                method="flat_rate",
                rate_applied=EXPENSE_40_1_RATE,
                cap_applied=EXPENSE_40_1_2_CAP,
                notes="Shared cap with 40(2)",
            ))

        if commission_total > 0:
            commission_share = (commission_total / combined_total) * flat_expense
            result.line_items.append(ExpenseLineItem(
                income_type=IncomeType.COMMISSION,
                income_amount=commission_total,
                expense_amount=commission_share,
                method="flat_rate",
                rate_applied=EXPENSE_40_2_RATE,
                cap_applied=EXPENSE_40_1_2_CAP,
                notes="Shared cap with 40(1)",
            ))

    def _calc_single_entry(self, entry: IncomeEntry) -> ExpenseLineItem:
        """คำนวณค่าใช้จ่ายสำหรับเงินได้รายการเดียว"""

        if entry.income_type == IncomeType.INTEREST_DIVIDEND:
            return ExpenseLineItem(
                income_type=entry.income_type,
                income_amount=entry.amount,
                expense_amount=0,
                method="none",
                rate_applied=EXPENSE_40_4_RATE,
                notes="40(4) cannot deduct expenses",
            )

        if entry.income_type == IncomeType.ROYALTY:
            return self._calc_with_optional_actual(
                entry, EXPENSE_40_3_RATE, EXPENSE_40_3_CAP
            )

        if entry.income_type == IncomeType.RENTAL:
            rate = EXPENSE_40_5_RATES.get(entry.sub_type or "other_property", 0.10)
            return self._calc_with_optional_actual(entry, rate, cap=None)

        if entry.income_type == IncomeType.PROFESSION:
            rate = EXPENSE_40_6_RATES.get(entry.sub_type or "other_profession", 0.30)
            return self._calc_with_optional_actual(entry, rate, cap=None)

        if entry.income_type == IncomeType.CONTRACTOR:
            return self._calc_with_optional_actual(
                entry, EXPENSE_40_7_RATE, cap=None
            )

        if entry.income_type == IncomeType.OTHER:
            rate = EXPENSE_40_8_RATES.get(entry.sub_type or "default", 0.40)
            return self._calc_with_optional_actual(entry, rate, cap=None)

        # Fallback (should not reach here)
        return ExpenseLineItem(
            income_type=entry.income_type,
            income_amount=entry.amount,
            expense_amount=0,
            method="unknown",
        )

    def _calc_with_optional_actual(
        self,
        entry: IncomeEntry,
        flat_rate: float,
        cap: float | None,
    ) -> ExpenseLineItem:
        """คำนวณค่าใช้จ่ายที่เลือกได้ระหว่างเหมากับตามจริง"""

        flat_expense = entry.amount * flat_rate
        if cap is not None:
            flat_expense = min(flat_expense, cap)

        if entry.expense_method == ExpenseMethod.ACTUAL and entry.actual_expense is not None:
            # Use whichever is higher: actual or flat (taxpayer's benefit)
            # Note: In practice, taxpayer chooses one method per income type
            actual = min(entry.actual_expense, entry.amount)  # Can't exceed income
            return ExpenseLineItem(
                income_type=entry.income_type,
                income_amount=entry.amount,
                expense_amount=actual,
                method="actual",
                notes=f"Actual expense chosen (flat would be {flat_expense:,.0f})",
            )

        return ExpenseLineItem(
            income_type=entry.income_type,
            income_amount=entry.amount,
            expense_amount=flat_expense,
            method="flat_rate",
            rate_applied=flat_rate,
            cap_applied=cap,
        )
