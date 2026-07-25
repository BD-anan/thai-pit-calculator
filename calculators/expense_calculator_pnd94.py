"""
Expense Deduction Calculator for PND 94 (ภ.ง.ด. 94).
คำนวณค่าใช้จ่ายสำหรับเงินได้ 40(5)-40(8) เท่านั้น

Business rules:
- เฉพาะ 40(5) ค่าเช่า, 40(6) วิชาชีพ, 40(7) รับเหมา, 40(8) อื่นๆ
- อัตราเหมาเท่าเดิม ใช้กับรายได้ครึ่งปี (ไม่หาร 2 ซ้ำ)
- 40(1)-40(4) ไม่มีหน้าที่ยื่น ภ.ง.ด. 94
"""

from dataclasses import dataclass, field

from models.income import IncomeType, IncomeEntry, TaxpayerIncome, ExpenseMethod
from config.tax_rates_2569_pnd94 import (
    EXPENSE_40_5_RATES, EXPENSE_40_6_RATES,
    EXPENSE_40_7_RATE, EXPENSE_40_8_RATES,
)

# Income types allowed in PND94
PND94_INCOME_TYPES = {
    IncomeType.RENTAL,       # 40(5)
    IncomeType.PROFESSION,   # 40(6)
    IncomeType.CONTRACTOR,   # 40(7)
    IncomeType.OTHER,        # 40(8)
}


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
    def total_income(self) -> float:
        return sum(item.income_amount for item in self.line_items)

    @property
    def income_after_expenses(self) -> float:
        return self.total_income - self.total_expenses


class ExpenseCalculatorPND94:
    """คำนวณค่าใช้จ่ายสำหรับ ภ.ง.ด. 94 — เฉพาะ 40(5)-40(8)"""

    def calculate(self, taxpayer_income: TaxpayerIncome) -> ExpenseResult:
        result = ExpenseResult()

        for entry in taxpayer_income.incomes:
            if entry.income_type not in PND94_INCOME_TYPES:
                raise ValueError(
                    f"Income type {entry.income_type.value} is not allowed "
                    f"in PND94. Only 40(5)-40(8) are accepted."
                )
            line_item = self._calc_entry(entry)
            result.line_items.append(line_item)

        return result

    def _calc_entry(self, entry: IncomeEntry) -> ExpenseLineItem:
        """คำนวณค่าใช้จ่ายสำหรับเงินได้รายการเดียว"""

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

        # Should not reach here due to validation above
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
            actual = min(entry.actual_expense, entry.amount)
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
