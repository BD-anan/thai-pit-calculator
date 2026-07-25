"""End-to-end tests for PND94 calculator — using user-provided examples."""
import pytest
from models.income import TaxpayerIncome, IncomeEntry, IncomeType, FilingStatus
from models.deductions import DeductionEntry, DeductionType
from main_pnd94 import ThaiPITCalculatorPND94


@pytest.fixture
def calc():
    return ThaiPITCalculatorPND94()


class TestUserExamples:
    """ตัวอย่างจากผู้ใช้"""

    def test_example_a_contractor_300k_tax_0(self, calc):
        """
        คุณเอ: 40(7) รับเหมา 300,000
        → expense 60% = 180,000
        → income after expense = 120,000
        → personal 30,000 + social security 5,250
        → net = 120,000 - 35,250 = 84,750
        → tax: 0 (อยู่ในช่อง 0-150k exempt)
        """
        income = TaxpayerIncome(filing_status=FilingStatus.SINGLE)
        income.add_income(IncomeEntry(IncomeType.CONTRACTOR, 300_000))

        deductions = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.SOCIAL_SECURITY, 5_250),
        ]

        result = calc.calculate(income, deductions)

        assert result.total_assessable_income == 300_000
        assert result.total_expenses == 180_000
        assert result.income_after_expenses == 120_000
        assert result.tax_payable == 0

    def test_example_b_rental_500k_tax_9500(self, calc):
        """
        คุณบี: 40(5) ค่าเช่าบ้าน 500,000
        → expense 30% = 150,000
        → income after expense = 350,000
        → personal 30,000
        → net = 350,000 - 30,000 = 320,000
        → tax: 150k×0% + 150k×5% + 20k×10% = 0 + 7,500 + 2,000 = 9,500
        """
        income = TaxpayerIncome(filing_status=FilingStatus.SINGLE)
        income.add_income(IncomeEntry(
            IncomeType.RENTAL, 500_000, sub_type="building",
        ))

        deductions = [
            DeductionEntry(DeductionType.PERSONAL),
        ]

        result = calc.calculate(income, deductions)

        assert result.total_assessable_income == 500_000
        assert result.total_expenses == 150_000
        assert result.income_after_expenses == 350_000
        assert result.total_deductions == 30_000
        assert result.net_income == 320_000
        assert result.tax_payable == 9_500


class TestFilingStatusValidation:
    """ตรวจสอบสถานะการยื่นแบบ"""

    def test_single_ok(self, calc):
        income = TaxpayerIncome(filing_status=FilingStatus.SINGLE)
        income.add_income(IncomeEntry(IncomeType.OTHER, 100_000))
        result = calc.calculate(income, [DeductionEntry(DeductionType.PERSONAL)])
        assert result is not None

    def test_married_sep_ok(self, calc):
        income = TaxpayerIncome(
            filing_status=FilingStatus.MARRIED_FILING_SEPARATELY,
        )
        income.add_income(IncomeEntry(IncomeType.OTHER, 100_000))
        result = calc.calculate(income, [DeductionEntry(DeductionType.PERSONAL)])
        assert result is not None

    def test_married_joint_rejected(self, calc):
        income = TaxpayerIncome(
            filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
        )
        income.add_income(IncomeEntry(IncomeType.OTHER, 100_000))
        with pytest.raises(ValueError, match="SINGLE or MARRIED_FILING_SEPARATELY"):
            calc.calculate(income, [DeductionEntry(DeductionType.PERSONAL)])


class TestIncomeTypeValidation:
    """ตรวจสอบประเภทเงินได้"""

    def test_salary_rejected(self, calc):
        income = TaxpayerIncome(filing_status=FilingStatus.SINGLE)
        income.add_income(IncomeEntry(IncomeType.SALARY, 500_000))
        with pytest.raises(ValueError, match="40\\(5\\)-40\\(8\\)"):
            calc.calculate(income, [DeductionEntry(DeductionType.PERSONAL)])


class TestFlatTaxComparison:
    """ภาษีเหมา 0.5%"""

    def test_flat_tax_not_applicable_under_1m(self, calc):
        """รายได้ < 1M → ไม่ใช้ภาษีเหมา"""
        income = TaxpayerIncome(filing_status=FilingStatus.SINGLE)
        income.add_income(IncomeEntry(IncomeType.CONTRACTOR, 800_000))

        result = calc.calculate(income, [DeductionEntry(DeductionType.PERSONAL)])
        assert result.flat_result.is_applicable is False
        assert result.comparison_result.chosen_method == "progressive"

    def test_flat_tax_applicable_over_1m(self, calc):
        """รายได้ >= 1M → ต้องเปรียบเทียบ"""
        income = TaxpayerIncome(filing_status=FilingStatus.SINGLE)
        income.add_income(IncomeEntry(IncomeType.CONTRACTOR, 2_000_000))

        result = calc.calculate(income, [DeductionEntry(DeductionType.PERSONAL)])
        assert result.flat_result.is_applicable is True
        # Flat: 2M * 0.5% = 10,000
        assert result.flat_result.tax_amount == 10_000


class TestOfficialFAQExample:
    """ตัวอย่างจาก Q&A สรรพากร — Q24"""

    def test_q24_life_40k_health_5k_annuity_200k(self, calc):
        """
        เงินได้ 800,000 (40(7))
        ประกันชีวิต 40,000 → tier1: 5,000 + tier2: 30,000 = 35,000
        ประกันสุขภาพ 5,000 → 5,000
        ชีวิต+สุขภาพ = 40,000 < 95,000 → ไม่โดน combined cap
        ประกันบำนาญ 200,000 → min(200k, 15%×800k=120k, 100k cap) = 100,000
        """
        income = TaxpayerIncome(filing_status=FilingStatus.SINGLE)
        income.add_income(IncomeEntry(IncomeType.CONTRACTOR, 800_000))

        deductions = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.LIFE_INSURANCE, 40_000),
            DeductionEntry(DeductionType.HEALTH_INSURANCE, 5_000),
            DeductionEntry(DeductionType.LIFE_INSURANCE_ANNUITY, 200_000),
        ]

        result = calc.calculate(income, deductions)

        # Find items
        life = None
        health = None
        annuity = None
        for item in result.deduction_result.line_items:
            if item.deduction_type == DeductionType.LIFE_INSURANCE:
                life = item
            elif item.deduction_type == DeductionType.HEALTH_INSURANCE:
                health = item
            elif item.deduction_type == DeductionType.LIFE_INSURANCE_ANNUITY:
                annuity = item

        assert life.final_amount == 35_000
        assert health.final_amount == 5_000
        assert annuity.final_amount == 100_000


class TestEdgeCases:
    """Edge cases"""

    def test_zero_income(self, calc):
        income = TaxpayerIncome(filing_status=FilingStatus.SINGLE)
        income.add_income(IncomeEntry(IncomeType.OTHER, 0))
        result = calc.calculate(income, [DeductionEntry(DeductionType.PERSONAL)])
        assert result.tax_payable == 0

    def test_no_deductions_except_personal(self, calc):
        income = TaxpayerIncome(filing_status=FilingStatus.SINGLE)
        income.add_income(IncomeEntry(IncomeType.OTHER, 100_000))
        result = calc.calculate(income, [DeductionEntry(DeductionType.PERSONAL)])
        # 100k * 40% = 40k expense → net income 60k → 60k - 30k = 30k
        # 30k < 150k exempt → tax 0
        assert result.tax_payable == 0
