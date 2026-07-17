"""
End-to-End Tests.
ทดสอบ pipeline ทั้งหมดจาก input ถึง output
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from models.income import (
    TaxpayerIncome, IncomeEntry, IncomeType, FilingStatus, ExpenseMethod,
)
from models.deductions import DeductionEntry, DeductionType
from main import ThaiPITCalculator


@pytest.fixture
def calculator():
    return ThaiPITCalculator()


class TestSalaryWorkerSimple:
    """มนุษย์เงินเดือน — กรณีง่าย"""

    def test_low_income_no_tax(self, calculator):
        """
        เงินเดือน 310,000/ปี
        ค่าใช้จ่าย: 100,000
        ค่าลดหย่อน: ส่วนตัว 60,000 + ประกันสังคม 9,000 = 69,000
        เงินได้สุทธิ: 310,000 - 100,000 - 69,000 = 141,000
        ภาษี: 0 (ไม่ถึง 150,000)
        """
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(IncomeType.SALARY, 310_000))
        deductions = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.SOCIAL_SECURITY, 9_000),
        ]
        result = calculator.calculate(income, deductions)
        assert result.net_income == 141_000
        assert result.tax_payable == 0

    def test_salary_worker_standard(self, calculator):
        """
        เงินเดือน 600,000/ปี (50,000/เดือน)
        ค่าใช้จ่าย: 100,000
        ค่าลดหย่อน: ส่วนตัว 60,000 + ประกันสังคม 9,000 = 69,000
        เงินได้สุทธิ: 600,000 - 100,000 - 69,000 = 431,000
        ภาษี: 7,500 + (431,000 - 300,000) x 10% = 7,500 + 13,100 = 20,600
        """
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(IncomeType.SALARY, 600_000))
        deductions = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.SOCIAL_SECURITY, 9_000),
        ]
        result = calculator.calculate(income, deductions)
        assert result.net_income == 431_000
        assert result.tax_payable == 20_600

    def test_salary_worker_with_deductions(self, calculator):
        """
        เงินเดือน 1,200,000/ปี (100,000/เดือน)
        ค่าใช้จ่าย: 100,000
        ค่าลดหย่อน:
          - ส่วนตัว 60,000
          - ประกันสังคม 9,000
          - ประกันชีวิต 80,000
          - ประกันสุขภาพ 15,000 → ชีวิต+สุขภาพ = 95,000 (< 100,000 cap)
          - RMF 200,000 (30% of 1.2M = 360k, cap 500k → 200k ok)
          - Thai ESG 100,000 (30% of 1.2M = 360k, cap 300k → 100k ok)
          รวมลดหย่อน: 60,000 + 9,000 + 95,000 + 200,000 + 100,000 = 464,000
        เงินได้สุทธิ: 1,200,000 - 100,000 - 464,000 = 636,000
        ภาษี: 7,500 + 20,000 + (636,000 - 500,000) x 15% = 27,500 + 20,400 = 47,900
        """
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(IncomeType.SALARY, 1_200_000))
        deductions = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.SOCIAL_SECURITY, 9_000),
            DeductionEntry(DeductionType.LIFE_INSURANCE, 80_000),
            DeductionEntry(DeductionType.HEALTH_INSURANCE, 15_000),
            DeductionEntry(DeductionType.RMF, 200_000),
            DeductionEntry(DeductionType.THAI_ESG, 100_000),
        ]
        result = calculator.calculate(income, deductions)
        assert result.net_income == 636_000
        assert result.tax_payable == 47_900


class TestMixedIncome:
    """เงินได้หลายประเภท"""

    def test_salary_plus_rental_below_flat_threshold(self, calculator):
        """
        เงินเดือน 800,000 + ค่าเช่าอาคาร 400,000
        ค่าใช้จ่าย: 100,000 (เงินเดือน) + 120,000 (ค่าเช่า 30%) = 220,000
        ค่าลดหย่อน: ส่วนตัว 60,000
        เงินได้สุทธิ: 1,200,000 - 220,000 - 60,000 = 920,000
        Flat tax: non-salary = 400,000 < 1,000,000 → ไม่ต้องคำนวณ
        ภาษีขั้นบันได: 0 + 7,500 + 20,000 + 37,500 + (920,000 - 750,000) x 20%
                      = 65,000 + 34,000 = 99,000
        """
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(IncomeType.SALARY, 800_000))
        income.add_income(IncomeEntry(IncomeType.RENTAL, 400_000, sub_type="building"))
        deductions = [
            DeductionEntry(DeductionType.PERSONAL),
        ]
        result = calculator.calculate(income, deductions)
        assert result.flat_result.is_applicable is False
        assert result.comparison_result.chosen_method == "progressive"

    def test_flat_tax_applicable(self, calculator):
        """
        เงินเดือน 500,000 + รับเหมา 2,000,000
        Flat tax: non-salary = 2,000,000 >= 1,000,000 → ต้องคำนวณ
        Flat tax = 2,000,000 x 0.5% = 10,000
        """
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(IncomeType.SALARY, 500_000))
        income.add_income(IncomeEntry(IncomeType.CONTRACTOR, 2_000_000))
        deductions = [
            DeductionEntry(DeductionType.PERSONAL),
        ]
        result = calculator.calculate(income, deductions)
        assert result.flat_result.is_applicable is True
        assert result.flat_result.tax_amount == 10_000
        # Progressive should be higher in this case
        assert result.tax_payable >= 10_000
