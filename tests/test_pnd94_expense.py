"""Tests for PND94 Expense Calculator."""
import pytest
from models.income import IncomeType, IncomeEntry, TaxpayerIncome, ExpenseMethod
from calculators.expense_calculator_pnd94 import ExpenseCalculatorPND94


@pytest.fixture
def calc():
    return ExpenseCalculatorPND94()


class TestPND94IncomeValidation:
    """PND94 ต้องรับเฉพาะ 40(5)-40(8)"""

    def test_reject_salary(self, calc):
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(IncomeType.SALARY, 500_000))
        with pytest.raises(ValueError, match="not allowed"):
            calc.calculate(tp)

    def test_reject_commission(self, calc):
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(IncomeType.COMMISSION, 100_000))
        with pytest.raises(ValueError, match="not allowed"):
            calc.calculate(tp)

    def test_reject_royalty(self, calc):
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(IncomeType.ROYALTY, 100_000))
        with pytest.raises(ValueError, match="not allowed"):
            calc.calculate(tp)

    def test_reject_interest_dividend(self, calc):
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(IncomeType.INTEREST_DIVIDEND, 50_000))
        with pytest.raises(ValueError, match="not allowed"):
            calc.calculate(tp)


class TestPND94ExpenseRates:
    """อัตราค่าใช้จ่ายเหมา — ใช้อัตราเต็ม × รายได้ครึ่งปี"""

    def test_rental_building_30pct(self, calc):
        """40(5) บ้าน 30%"""
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(IncomeType.RENTAL, 500_000, sub_type="building"))
        result = calc.calculate(tp)
        assert result.total_expenses == 150_000

    def test_rental_farmland_20pct(self, calc):
        """40(5) ที่ดินเกษตร 20%"""
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(IncomeType.RENTAL, 200_000, sub_type="farmland"))
        result = calc.calculate(tp)
        assert result.total_expenses == 40_000

    def test_rental_other_land_15pct(self, calc):
        """40(5) ที่ดินอื่น 15%"""
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(IncomeType.RENTAL, 100_000, sub_type="other_land"))
        result = calc.calculate(tp)
        assert result.total_expenses == 15_000

    def test_profession_medical_60pct(self, calc):
        """40(6) โรคศิลปะ 60%"""
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(IncomeType.PROFESSION, 1_000_000, sub_type="medical"))
        result = calc.calculate(tp)
        assert result.total_expenses == 600_000

    def test_profession_law_30pct(self, calc):
        """40(6) กฎหมาย 30%"""
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(IncomeType.PROFESSION, 400_000, sub_type="law"))
        result = calc.calculate(tp)
        assert result.total_expenses == 120_000

    def test_contractor_60pct(self, calc):
        """40(7) รับเหมา 60% — ตัวอย่างคุณเอ"""
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(IncomeType.CONTRACTOR, 300_000))
        result = calc.calculate(tp)
        assert result.total_expenses == 180_000
        assert result.income_after_expenses == 120_000

    def test_other_default_40pct(self, calc):
        """40(8) default 40%"""
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(IncomeType.OTHER, 200_000))
        result = calc.calculate(tp)
        assert result.total_expenses == 80_000

    def test_other_special_60pct(self, calc):
        """40(8) special 60%"""
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(IncomeType.OTHER, 200_000, sub_type="special_60"))
        result = calc.calculate(tp)
        assert result.total_expenses == 120_000


class TestPND94ActualExpense:
    """หักตามจริง"""

    def test_contractor_actual(self, calc):
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(
            IncomeType.CONTRACTOR, 300_000,
            expense_method=ExpenseMethod.ACTUAL, actual_expense=200_000,
        ))
        result = calc.calculate(tp)
        assert result.total_expenses == 200_000

    def test_actual_cannot_exceed_income(self, calc):
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(
            IncomeType.OTHER, 100_000,
            expense_method=ExpenseMethod.ACTUAL, actual_expense=150_000,
        ))
        result = calc.calculate(tp)
        assert result.total_expenses == 100_000


class TestPND94MultipleIncomes:
    """หลายประเภทรวมกัน"""

    def test_mixed_rental_and_contractor(self, calc):
        tp = TaxpayerIncome()
        tp.add_income(IncomeEntry(IncomeType.RENTAL, 500_000, sub_type="building"))
        tp.add_income(IncomeEntry(IncomeType.CONTRACTOR, 300_000))
        result = calc.calculate(tp)
        # 500k * 30% + 300k * 60% = 150k + 180k = 330k
        assert result.total_expenses == 330_000
        assert result.income_after_expenses == 470_000
