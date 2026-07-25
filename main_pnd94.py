"""
Thai Personal Income Tax Calculator — PND 94 (ภ.ง.ด. 94) Orchestrator
คำนวณภาษีเงินได้บุคคลธรรมดา ครึ่งปี (ม.ค. - มิ.ย.) ปีภาษี 2569

Pipeline:
1. รับ input — เงินได้ 40(5)-40(8) + ค่าลดหย่อน
2. Validate — เฉพาะ 40(5)-40(8), เฉพาะ single/married_sep
3. คำนวณค่าใช้จ่าย → เงินได้หลังหักค่าใช้จ่าย
4. คำนวณค่าลดหย่อน (halved caps, 2-tier life insurance)
5. คำนวณภาษีวิธีขั้นบันได
6. คำนวณภาษีวิธีเหมา 0.5%
7. เปรียบเทียบ → ภาษีที่ต้องชำระ
"""

from dataclasses import dataclass

from models.income import (
    TaxpayerIncome, IncomeType, IncomeEntry, FilingStatus, ExpenseMethod,
)
from models.deductions import DeductionEntry, DeductionType
from calculators.expense_calculator_pnd94 import (
    ExpenseCalculatorPND94, ExpenseResult, PND94_INCOME_TYPES,
)
from calculators.deduction_calculator_pnd94 import (
    DeductionCalculatorPND94, DeductionResult,
)
from calculators.progressive_tax_pnd94 import (
    ProgressiveTaxCalculatorPND94, ProgressiveTaxResult,
)
from calculators.flat_tax_pnd94 import (
    FlatTaxCalculatorPND94, FlatTaxResult,
)
from calculators.tax_comparator import TaxComparator, TaxComparisonResult


# Filing statuses allowed in PND94 (Phase 1)
PND94_FILING_STATUSES = {
    FilingStatus.SINGLE,
    FilingStatus.MARRIED_FILING_SEPARATELY,
}


@dataclass
class TaxCalculationResultPND94:
    """
    Structured result สำหรับ ภ.ง.ด. 94
    """
    # Input
    taxpayer_income: TaxpayerIncome
    deduction_entries: list[DeductionEntry]

    # Step results
    expense_result: ExpenseResult
    deduction_result: DeductionResult
    progressive_result: ProgressiveTaxResult
    flat_result: FlatTaxResult
    comparison_result: TaxComparisonResult

    # Summary
    total_assessable_income: float
    total_expenses: float
    income_after_expenses: float
    total_deductions: float
    net_income: float
    tax_payable: float


class ThaiPITCalculatorPND94:
    """Main orchestrator สำหรับ ภ.ง.ด. 94"""

    def __init__(self):
        self.expense_calc = ExpenseCalculatorPND94()
        self.deduction_calc = DeductionCalculatorPND94()
        self.progressive_calc = ProgressiveTaxCalculatorPND94()
        self.flat_calc = FlatTaxCalculatorPND94()
        self.comparator = TaxComparator()

    def calculate(
        self,
        taxpayer_income: TaxpayerIncome,
        deduction_entries: list[DeductionEntry],
    ) -> TaxCalculationResultPND94:

        # Validate filing status
        if taxpayer_income.filing_status not in PND94_FILING_STATUSES:
            raise ValueError(
                f"PND94 only supports SINGLE or MARRIED_FILING_SEPARATELY. "
                f"Got: {taxpayer_income.filing_status.value}"
            )

        # Validate income types
        for entry in taxpayer_income.incomes:
            if entry.income_type not in PND94_INCOME_TYPES:
                raise ValueError(
                    f"PND94 only allows 40(5)-40(8). "
                    f"Got: {entry.income_type.value}"
                )

        # Step 1: Total assessable income
        total_assessable = taxpayer_income.total_assessable_income()

        # Step 2: Calculate expenses
        expense_result = self.expense_calc.calculate(taxpayer_income)
        total_expenses = expense_result.total_expenses
        income_after_expenses = expense_result.income_after_expenses

        # Step 3: Calculate deductions
        deduction_result = self.deduction_calc.calculate(
            entries=deduction_entries,
            assessable_income=total_assessable,
            income_after_expenses=income_after_expenses,
        )
        total_deductions = deduction_result.total_deductions

        # Step 4: Net income
        net_income = max(income_after_expenses - total_deductions, 0)

        # Step 5: Progressive tax
        progressive_result = self.progressive_calc.calculate(net_income)

        # Step 6: Flat tax — PND94 uses total income (all are non-salary)
        flat_result = self.flat_calc.calculate(total_assessable)

        # Step 7: Compare
        comparison_result = self.comparator.compare(
            progressive_result, flat_result
        )

        return TaxCalculationResultPND94(
            taxpayer_income=taxpayer_income,
            deduction_entries=deduction_entries,
            expense_result=expense_result,
            deduction_result=deduction_result,
            progressive_result=progressive_result,
            flat_result=flat_result,
            comparison_result=comparison_result,
            total_assessable_income=total_assessable,
            total_expenses=total_expenses,
            income_after_expenses=income_after_expenses,
            total_deductions=total_deductions,
            net_income=net_income,
            tax_payable=comparison_result.tax_payable,
        )


def print_result(result: TaxCalculationResultPND94) -> None:
    """แสดงผลลัพธ์แบบ CLI"""

    print("=" * 60)
    print("  Thai PIT — ภ.ง.ด. 94 ครึ่งปี 2569 (ม.ค.-มิ.ย.)")
    print("=" * 60)

    # 1. Income
    print("\n📋 เงินได้พึงประเมิน 40(5)-40(8)")
    print("-" * 40)
    for item in result.expense_result.line_items:
        print(f"  {item.income_type.value:8s}  {item.income_amount:>14,.0f} THB")
    print(f"  {'รวม':8s}  {result.total_assessable_income:>14,.0f} THB")

    # 2. Expenses
    print(f"\n📋 ค่าใช้จ่าย")
    print("-" * 40)
    for item in result.expense_result.line_items:
        method_str = f"({item.method})"
        print(f"  {item.income_type.value:8s}  {item.expense_amount:>14,.0f} THB  {method_str}")
    print(f"  {'รวม':8s}  {result.total_expenses:>14,.0f} THB")
    print(f"  เงินได้หลังหักค่าใช้จ่าย: {result.income_after_expenses:>14,.0f} THB")

    # 3. Deductions
    print(f"\n📋 ค่าลดหย่อน (ครึ่งปี)")
    print("-" * 40)
    for item in result.deduction_result.line_items:
        print(f"  {item.deduction_type.value:25s}  {item.final_amount:>12,.0f} THB")
        if item.notes:
            print(f"  {'':25s}  {item.notes}")
    print(f"  {'รวม':25s}  {result.total_deductions:>12,.0f} THB")

    # 4. Net income
    print(f"\n📋 เงินได้สุทธิ: {result.net_income:>14,.0f} THB")

    # 5. Progressive tax
    print(f"\n📋 ภาษีวิธีขั้นบันได")
    print("-" * 40)
    for b in result.progressive_result.brackets:
        upper_str = f"{b.bracket_upper:,.0f}" if b.bracket_upper else "unlimited"
        print(
            f"  {b.bracket_lower:>12,.0f} - {upper_str:>12s}  "
            f"@{b.rate:5.0%}  = {b.tax_in_bracket:>10,.0f} THB"
        )
    print(f"  {'รวม':>28s}        = {result.progressive_result.total_tax:>10,.0f} THB")

    # 6. Flat tax
    print(f"\n📋 ภาษีวิธีเหมา 0.5%")
    print("-" * 40)
    print(f"  {result.flat_result.reason}")

    # 7. Comparison
    print(f"\n📋 เปรียบเทียบ")
    print("-" * 40)
    print(f"  {result.comparison_result.explanation}")

    # 8. Final
    print(f"\n{'=' * 60}")
    print(f"  💰 ภาษีที่ต้องชำระ (ครึ่งปี): {result.tax_payable:>14,.0f} THB")
    print(f"{'=' * 60}")


# =============================================================================
# Example usage
# =============================================================================
if __name__ == "__main__":
    # ตัวอย่างคุณเอ: 40(7) รับเหมา 300,000 → expense 180,000 → net 90,000 → tax 0
    income_a = TaxpayerIncome(filing_status=FilingStatus.SINGLE)
    income_a.add_income(IncomeEntry(
        income_type=IncomeType.CONTRACTOR,
        amount=300_000,
    ))

    deductions_a = [
        DeductionEntry(DeductionType.PERSONAL),
        DeductionEntry(DeductionType.SOCIAL_SECURITY, 5_250),
    ]

    calculator = ThaiPITCalculatorPND94()
    result_a = calculator.calculate(income_a, deductions_a)
    print_result(result_a)

    print("\n\n")

    # ตัวอย่างคุณบี: 40(5) ค่าเช่า 500,000 → expense 150,000 → net 320,000 → tax 9,500
    income_b = TaxpayerIncome(filing_status=FilingStatus.SINGLE)
    income_b.add_income(IncomeEntry(
        income_type=IncomeType.RENTAL,
        amount=500_000,
        sub_type="building",
    ))

    deductions_b = [
        DeductionEntry(DeductionType.PERSONAL),
    ]

    result_b = calculator.calculate(income_b, deductions_b)
    print_result(result_b)
