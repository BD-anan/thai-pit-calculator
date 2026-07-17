"""
Tests for ExpenseCalculator.
ทดสอบการหักค่าใช้จ่ายตามประเภทเงินได้
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from models.income import (
    TaxpayerIncome, IncomeEntry, IncomeType, FilingStatus, ExpenseMethod,
)
from calculators.expense_calculator import ExpenseCalculator


@pytest.fixture
def calc():
    return ExpenseCalculator()


class TestSalaryExpense:
    """40(1) เงินเดือน"""

    def test_salary_below_cap(self, calc):
        """เงินเดือน 150,000 → ค่าใช้จ่าย 75,000 (50% < 100,000)"""
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(IncomeType.SALARY, 150_000))
        result = calc.calculate(income)
        assert result.total_expenses == 75_000

    def test_salary_at_cap(self, calc):
        """เงินเดือน 200,000 → ค่าใช้จ่าย 100,000 (50% = 100,000)"""
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(IncomeType.SALARY, 200_000))
        result = calc.calculate(income)
        assert result.total_expenses == 100_000

    def test_salary_above_cap(self, calc):
        """เงินเดือน 1,000,000 → ค่าใช้จ่าย 100,000 (cap)"""
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(IncomeType.SALARY, 1_000_000))
        result = calc.calculate(income)
        assert result.total_expenses == 100_000


class TestSalaryCommissionSharedCap:
    """40(1) + 40(2) เพดานร่วม"""

    def test_combined_below_cap(self, calc):
        """เงินเดือน 100,000 + นายหน้า 50,000 = 150,000 → ค่าใช้จ่าย 75,000"""
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(IncomeType.SALARY, 100_000))
        income.add_income(IncomeEntry(IncomeType.COMMISSION, 50_000))
        result = calc.calculate(income)
        assert result.total_expenses == 75_000

    def test_combined_at_cap(self, calc):
        """เงินเดือน 500,000 + นายหน้า 500,000 → ค่าใช้จ่าย 100,000 (cap)"""
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(IncomeType.SALARY, 500_000))
        income.add_income(IncomeEntry(IncomeType.COMMISSION, 500_000))
        result = calc.calculate(income)
        assert result.total_expenses == 100_000

    def test_separate_would_exceed_but_shared_caps(self, calc):
        """
        ถ้าแยก cap แต่ละตัวจะได้ 100k + 100k = 200k
        แต่เพดานร่วมต้องได้แค่ 100k
        """
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(IncomeType.SALARY, 300_000))
        income.add_income(IncomeEntry(IncomeType.COMMISSION, 300_000))
        result = calc.calculate(income)
        assert result.total_expenses == 100_000


class TestInterestDividend:
    """40(4) ดอกเบี้ย เงินปันผล — หักค่าใช้จ่ายไม่ได้"""

    def test_no_expense(self, calc):
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(IncomeType.INTEREST_DIVIDEND, 500_000))
        result = calc.calculate(income)
        assert result.total_expenses == 0


class TestRentalExpense:
    """40(5) ค่าเช่า"""

    def test_building_30pct(self, calc):
        """ค่าเช่าอาคาร 100,000 → ค่าใช้จ่าย 30,000 (30%)"""
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(
            IncomeType.RENTAL, 100_000, sub_type="building"
        ))
        result = calc.calculate(income)
        assert result.total_expenses == 30_000

    def test_actual_expense(self, calc):
        """เลือกหักตามจริง"""
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(
            IncomeType.RENTAL, 100_000,
            sub_type="building",
            expense_method=ExpenseMethod.ACTUAL,
            actual_expense=40_000,
        ))
        result = calc.calculate(income)
        assert result.total_expenses == 40_000


class TestMixedIncome:
    """รวมเงินได้หลายประเภท"""

    def test_salary_plus_rental(self, calc):
        """เงินเดือน 1,000,000 + ค่าเช่าอาคาร 200,000"""
        income = TaxpayerIncome()
        income.add_income(IncomeEntry(IncomeType.SALARY, 1_000_000))
        income.add_income(IncomeEntry(
            IncomeType.RENTAL, 200_000, sub_type="building"
        ))
        result = calc.calculate(income)
        # Salary: 100,000 (cap) + Rental: 60,000 (30%)
        assert result.total_expenses == 160_000
        assert result.income_after_expenses == 1_040_000
