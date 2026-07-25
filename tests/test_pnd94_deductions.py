"""Tests for PND94 Deduction Calculator."""
import pytest
from models.deductions import DeductionEntry, DeductionType
from calculators.deduction_calculator_pnd94 import DeductionCalculatorPND94


@pytest.fixture
def calc():
    return DeductionCalculatorPND94()


def _find(result, dt):
    """Find a deduction line item by type."""
    for item in result.line_items:
        if item.deduction_type == dt:
            return item
    return None


class TestPND94PersonalAllowances:
    """ค่าลดหย่อนส่วนตัว — ครึ่งของเต็มปี"""

    def test_personal_30k(self, calc):
        entries = [DeductionEntry(DeductionType.PERSONAL)]
        result = calc.calculate(entries, 500_000, 350_000)
        item = _find(result, DeductionType.PERSONAL)
        assert item.final_amount == 30_000

    def test_spouse_30k(self, calc):
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.SPOUSE),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        assert _find(result, DeductionType.SPOUSE).final_amount == 30_000

    def test_child_15k(self, calc):
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.CHILD, count=2),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        assert _find(result, DeductionType.CHILD).final_amount == 30_000

    def test_child_2018_plus_30k(self, calc):
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.CHILD_BORN_2018_PLUS, count=1),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        assert _find(result, DeductionType.CHILD_BORN_2018_PLUS).final_amount == 30_000

    def test_parent_15k(self, calc):
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.PARENT, count=2),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        assert _find(result, DeductionType.PARENT).final_amount == 30_000

    def test_disabled_30k(self, calc):
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.DISABLED_PERSON, count=1),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        assert _find(result, DeductionType.DISABLED_PERSON).final_amount == 30_000


class TestPND94LifeInsuranceSpecial:
    """ประกันชีวิต — กรณีพิเศษ 2 tier"""

    def test_under_10k_halved(self, calc):
        """จ่าย 8,000 → ส่วนแรก 8,000×50% = 4,000"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.LIFE_INSURANCE, 8_000),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        item = _find(result, DeductionType.LIFE_INSURANCE)
        assert item.final_amount == 4_000

    def test_exactly_10k(self, calc):
        """จ่าย 10,000 → ส่วนแรก 10,000×50% = 5,000"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.LIFE_INSURANCE, 10_000),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        item = _find(result, DeductionType.LIFE_INSURANCE)
        assert item.final_amount == 5_000

    def test_40k_two_tiers(self, calc):
        """จ่าย 40,000 → tier1: 5,000 + tier2: 30,000 = 35,000"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.LIFE_INSURANCE, 40_000),
        ]
        result = calc.calculate(entries, 800_000, 500_000)
        item = _find(result, DeductionType.LIFE_INSURANCE)
        assert item.final_amount == 35_000

    def test_100k_max(self, calc):
        """จ่าย 100,000 → tier1: 5,000 + tier2: 90,000 = 95,000"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.LIFE_INSURANCE, 100_000),
        ]
        result = calc.calculate(entries, 1_000_000, 600_000)
        item = _find(result, DeductionType.LIFE_INSURANCE)
        assert item.final_amount == 95_000

    def test_200k_capped_at_95k(self, calc):
        """จ่าย 200,000 → tier1: 5,000 + tier2: 90,000 = 95,000 (capped)"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.LIFE_INSURANCE, 200_000),
        ]
        result = calc.calculate(entries, 1_000_000, 600_000)
        item = _find(result, DeductionType.LIFE_INSURANCE)
        assert item.final_amount == 95_000


class TestPND94LifeHealthCombined:
    """ประกันชีวิต + สุขภาพ รวมไม่เกิน 95,000"""

    def test_life_and_health_under_cap(self, calc):
        """ชีวิต 40k→35k + สุขภาพ 5k = 40k < 95k"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.LIFE_INSURANCE, 40_000),
            DeductionEntry(DeductionType.HEALTH_INSURANCE, 5_000),
        ]
        result = calc.calculate(entries, 800_000, 500_000)
        life = _find(result, DeductionType.LIFE_INSURANCE)
        health = _find(result, DeductionType.HEALTH_INSURANCE)
        assert life.final_amount == 35_000
        assert health.final_amount == 5_000
        assert life.final_amount + health.final_amount == 40_000

    def test_life_and_health_at_cap(self, calc):
        """ชีวิต 100k→95k + สุขภาพ 12.5k → combined cap 95k"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.LIFE_INSURANCE, 100_000),
            DeductionEntry(DeductionType.HEALTH_INSURANCE, 12_500),
        ]
        result = calc.calculate(entries, 1_000_000, 600_000)
        life = _find(result, DeductionType.LIFE_INSURANCE)
        health = _find(result, DeductionType.HEALTH_INSURANCE)
        assert life.final_amount + health.final_amount <= 95_000

    def test_health_cap_25000(self, calc):
        """ประกันสุขภาพ cap 25,000 (ไม่หาร 2)"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.HEALTH_INSURANCE, 30_000),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        item = _find(result, DeductionType.HEALTH_INSURANCE)
        assert item.final_amount == 25_000


class TestPND94RetirementGroup:
    """กลุ่มเกษียณ — เฉพาะ บำนาญ + RMF + กอช."""

    def test_annuity_cap_100k(self, calc):
        """บำนาญ cap 100,000 (200k/2)"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.LIFE_INSURANCE_ANNUITY, 150_000),
        ]
        result = calc.calculate(entries, 1_000_000, 600_000)
        item = _find(result, DeductionType.LIFE_INSURANCE_ANNUITY)
        assert item.final_amount == 100_000

    def test_rmf_cap_250k(self, calc):
        """RMF cap 250,000 (500k/2)"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.RMF, 300_000),
        ]
        result = calc.calculate(entries, 2_000_000, 1_200_000)
        item = _find(result, DeductionType.RMF)
        assert item.final_amount == 250_000

    def test_rmf_pct_cap(self, calc):
        """RMF 30% of income if lower than hard cap"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.RMF, 200_000),
        ]
        result = calc.calculate(entries, 500_000, 300_000)
        item = _find(result, DeductionType.RMF)
        # 30% of 500k = 150k < 250k hard cap
        assert item.final_amount == 150_000

    def test_nsf_cap_15k(self, calc):
        """กอช. cap 15,000 (30k/2)"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.NATIONAL_SAVINGS_FUND, 20_000),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        item = _find(result, DeductionType.NATIONAL_SAVINGS_FUND)
        assert item.final_amount == 15_000

    def test_retirement_group_cap_500k(self, calc):
        """กลุ่มเกษียณรวมไม่เกิน 500,000"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.LIFE_INSURANCE_ANNUITY, 100_000),
            DeductionEntry(DeductionType.RMF, 300_000),
            DeductionEntry(DeductionType.NATIONAL_SAVINGS_FUND, 15_000),
        ]
        result = calc.calculate(entries, 2_000_000, 1_200_000)
        annuity = _find(result, DeductionType.LIFE_INSURANCE_ANNUITY)
        rmf = _find(result, DeductionType.RMF)
        nsf = _find(result, DeductionType.NATIONAL_SAVINGS_FUND)
        total = annuity.final_amount + rmf.final_amount + nsf.final_amount
        assert total <= 500_000


class TestPND94ESG:
    """Thai ESG — แยกวง"""

    def test_thai_esg_cap_150k(self, calc):
        """Thai ESG cap 150,000 (300k/2)"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.THAI_ESG, 200_000),
        ]
        result = calc.calculate(entries, 1_000_000, 600_000)
        item = _find(result, DeductionType.THAI_ESG)
        assert item.final_amount == 150_000

    def test_thai_esgx_cap_25k(self, calc):
        """Thai ESGX cap 25,000 (50k/2)"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.THAI_ESGX, 30_000),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        item = _find(result, DeductionType.THAI_ESGX)
        assert item.final_amount == 25_000


class TestPND94Stimulus:
    """กลุ่ม C: กระตุ้นเศรษฐกิจ"""

    def test_home_loan_interest_50k(self, calc):
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.HOME_LOAN_INTEREST, 80_000),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        item = _find(result, DeductionType.HOME_LOAN_INTEREST)
        assert item.final_amount == 50_000

    def test_solar_rooftop_100k(self, calc):
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.SOLAR_ROOFTOP, 150_000),
        ]
        result = calc.calculate(entries, 1_000_000, 600_000)
        item = _find(result, DeductionType.SOLAR_ROOFTOP)
        assert item.final_amount == 100_000

    def test_social_enterprise_50k(self, calc):
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.SOCIAL_ENTERPRISE, 80_000),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        item = _find(result, DeductionType.SOCIAL_ENTERPRISE)
        assert item.final_amount == 50_000

    def test_energy_saving_no_cap(self, calc):
        """ฉลากประหยัดไฟฟ้า — ไม่มีเพดาน"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.ENERGY_SAVING, 500_000),
        ]
        result = calc.calculate(entries, 1_000_000, 600_000)
        item = _find(result, DeductionType.ENERGY_SAVING)
        assert item.final_amount == 500_000

    def test_cctv_no_cap(self, calc):
        """กล้องวงจรปิด — ไม่มีเพดาน"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.CCTV, 200_000),
        ]
        result = calc.calculate(entries, 1_000_000, 600_000)
        item = _find(result, DeductionType.CCTV)
        assert item.final_amount == 200_000


class TestPND94SocialSecurity:
    """ประกันสังคม 2569"""

    def test_social_security_cap_5250(self, calc):
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.SOCIAL_SECURITY, 10_000),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        item = _find(result, DeductionType.SOCIAL_SECURITY)
        assert item.final_amount == 5_250


class TestPND94Donations:
    """บริจาค — cap หาร 2"""

    def test_donation_double_5pct_cap(self, calc):
        """บริจาค 2 เท่า cap 5% แทน 10%"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.DONATION_DOUBLE, 100_000),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        item = _find(result, DeductionType.DONATION_DOUBLE)
        # base = 350,000 - 30,000(personal) = 320,000
        # 5% of 320,000 = 16,000
        # doubled = 200,000
        # min(200k, 16k) = 16,000
        assert item.final_amount == 16_000

    def test_donation_general_5pct_cap(self, calc):
        """บริจาคทั่วไป cap 5%"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.DONATION_GENERAL, 50_000),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        item = _find(result, DeductionType.DONATION_GENERAL)
        # base = 350,000 - 30,000 = 320,000
        # 5% of 320,000 = 16,000
        # min(50k, 16k) = 16,000
        assert item.final_amount == 16_000

    def test_political_party_5k(self, calc):
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.POLITICAL_PARTY, 8_000),
        ]
        result = calc.calculate(entries, 500_000, 350_000)
        item = _find(result, DeductionType.POLITICAL_PARTY)
        assert item.final_amount == 5_000

    def test_donation_sequential_order(self, calc):
        """บริจาค 2 เท่าคิดก่อน → ทั่วไปคิดจากฐานที่เหลือ"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.DONATION_DOUBLE, 100_000),
            DeductionEntry(DeductionType.DONATION_GENERAL, 100_000),
        ]
        result = calc.calculate(entries, 1_000_000, 600_000)
        double_item = _find(result, DeductionType.DONATION_DOUBLE)
        general_item = _find(result, DeductionType.DONATION_GENERAL)
        # base = 600k - 30k = 570k
        # double: min(200k, 570k*5%=28.5k) = 28,500
        assert double_item.final_amount == 28_500
        # general base = 570k - 28.5k = 541,500
        # min(100k, 541500*5%=27075) = 27,075
        assert general_item.final_amount == 27_075
