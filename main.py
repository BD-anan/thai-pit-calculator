"""
Thai Personal Income Tax Calculator — Main Orchestrator
โปรแกรมคำนวณภาษีเงินได้บุคคลธรรมดา ปีภาษี 2568

Pipeline:
1. รับ input (เงินได้ + ค่าลดหย่อน)
2. คำนวณค่าใช้จ่าย → เงินได้หลังหักค่าใช้จ่าย
3. คำนวณค่าลดหย่อน → เงินได้สุทธิ
4. คำนวณภาษีวิธีขั้นบันได
5. คำนวณภาษีวิธีเหมา (ถ้า applicable)
6. เปรียบเทียบ → ภาษีที่ต้องชำระ
"""

from dataclasses import dataclass, field

from models.income import TaxpayerIncome, IncomeType, IncomeEntry, FilingStatus
from models.deductions import DeductionEntry, DeductionType
from calculators.expense_calculator import ExpenseCalculator, ExpenseResult
from calculators.deduction_calculator import DeductionCalculator, DeductionResult
from calculators.progressive_tax import ProgressiveTaxCalculator, ProgressiveTaxResult
from calculators.flat_tax import FlatTaxCalculator, FlatTaxResult
from calculators.tax_comparator import TaxComparator, TaxComparisonResult


@dataclass
class TaxCalculationResult:
    """
    Structured result — เก็บทุกขั้นตอนการคำนวณ
    ใช้ได้ทั้ง CLI, web, JSON, หรือ presentation layer ใดก็ได้
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


class ThaiPITCalculator:
    """Main orchestrator: รับ input → ส่งผ่านแต่ละ step → output"""

    def __init__(self):
        self.expense_calc = ExpenseCalculator()
        self.deduction_calc = DeductionCalculator()
        self.progressive_calc = ProgressiveTaxCalculator()
        self.flat_calc = FlatTaxCalculator()
        self.comparator = TaxComparator()

    def calculate(
        self,
        taxpayer_income: TaxpayerIncome,
        deduction_entries: list[DeductionEntry],
    ) -> TaxCalculationResult:
        """
        คำนวณภาษีเงินได้บุคคลธรรมดาทั้ง pipeline

        Args:
            taxpayer_income: ข้อมูลเงินได้ทั้งหมด
            deduction_entries: รายการค่าลดหย่อนทั้งหมด
        """

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

        # Step 6: Flat tax
        non_salary_income = taxpayer_income.total_non_salary()
        flat_result = self.flat_calc.calculate(non_salary_income)

        # Step 7: Compare and determine tax payable
        comparison_result = self.comparator.compare(
            progressive_result, flat_result
        )

        return TaxCalculationResult(
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


def print_result(result: TaxCalculationResult) -> None:
    """แสดงผลลัพธ์แบบ CLI (ตัวอย่าง presentation layer)"""

    print("=" * 60)
    print("  Thai Personal Income Tax Calculation — ปีภาษี 2568")
    print("=" * 60)

    # 1. Income summary
    print("\n📋 เงินได้พึงประเมิน")
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
        if item.notes:
            print(f"           ℹ️  {item.notes}")
    print(f"  {'รวม':8s}  {result.total_expenses:>14,.0f} THB")
    print(f"  เงินได้หลังหักค่าใช้จ่าย: {result.income_after_expenses:>14,.0f} THB")

    # 3. Deductions
    print(f"\n📋 ค่าลดหย่อน")
    print("-" * 40)
    for item in result.deduction_result.line_items:
        print(f"  {item.deduction_type.value:25s}  {item.final_amount:>12,.0f} THB")
        if item.cap_applied:
            print(f"  {'':25s}  cap: {item.cap_applied}")
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
    if result.flat_result.is_applicable and not result.flat_result.is_exempted:
        print(f"  ภาษีเหมา: {result.flat_result.tax_amount:>14,.0f} THB")

    # 7. Comparison
    print(f"\n📋 เปรียบเทียบ")
    print("-" * 40)
    print(f"  {result.comparison_result.explanation}")

    # 8. Final
    print(f"\n{'=' * 60}")
    print(f"  💰 ภาษีที่ต้องชำระ: {result.tax_payable:>14,.0f} THB")
    print(f"{'=' * 60}")


# =============================================================================
# Example usage
# =============================================================================
if __name__ == "__main__":
    from models.income import ExpenseMethod

    # ตัวอย่าง: มนุษย์เงินเดือน รายได้ 1,200,000 บาท/ปี
    income = TaxpayerIncome(filing_status=FilingStatus.SINGLE)
    income.add_income(IncomeEntry(
        income_type=IncomeType.SALARY,
        amount=1_200_000,
    ))

    deductions = [
        DeductionEntry(DeductionType.PERSONAL),             # ส่วนตัว 60,000
        DeductionEntry(DeductionType.SOCIAL_SECURITY, 9_000),  # ประกันสังคม
        DeductionEntry(DeductionType.LIFE_INSURANCE, 80_000),  # ประกันชีวิต
        DeductionEntry(DeductionType.HEALTH_INSURANCE, 15_000),  # ประกันสุขภาพ
        DeductionEntry(DeductionType.RMF, 200_000),           # RMF
        DeductionEntry(DeductionType.THAI_ESG, 100_000),      # Thai ESG
    ]

    calculator = ThaiPITCalculator()
    result = calculator.calculate(income, deductions)
    print_result(result)
