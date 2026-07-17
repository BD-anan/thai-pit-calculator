"""
Tests for DeductionCalculator.
ทดสอบการคำนวณค่าลดหย่อน
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from models.deductions import DeductionEntry, DeductionType
from calculators.deduction_calculator import DeductionCalculator


@pytest.fixture
def calc():
    return DeductionCalculator()


class TestPersonalDeductions:
    """กลุ่ม A: ส่วนตัวและครอบครัว"""

    def test_personal_allowance(self, calc):
        """ค่าลดหย่อนส่วนตัว 60,000"""
        entries = [DeductionEntry(DeductionType.PERSONAL)]
        result = calc.calculate(entries, 1_000_000, 900_000)
        personal = [i for i in result.line_items if i.deduction_type == DeductionType.PERSONAL]
        assert personal[0].final_amount == 60_000

    def test_child_allowance(self, calc):
        """บุตร 2 คน (เกิดก่อน 2561) → 60,000"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.CHILD, count=2),
        ]
        result = calc.calculate(entries, 1_000_000, 900_000)
        child = [i for i in result.line_items if i.deduction_type == DeductionType.CHILD]
        assert child[0].final_amount == 60_000  # 30,000 x 2

    def test_parent_allowance(self, calc):
        """บิดามารดา 2 คน → 60,000"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.PARENT, count=2),
        ]
        result = calc.calculate(entries, 1_000_000, 900_000)
        parent = [i for i in result.line_items if i.deduction_type == DeductionType.PARENT]
        assert parent[0].final_amount == 60_000  # 30,000 x 2


class TestInsuranceCaps:
    """กลุ่ม B: ประกันและการออม — cap logic"""

    def test_life_insurance_cap(self, calc):
        """ประกันชีวิต 120,000 → cap ที่ 100,000"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.LIFE_INSURANCE, 120_000),
        ]
        result = calc.calculate(entries, 1_000_000, 900_000)
        life = [i for i in result.line_items if i.deduction_type == DeductionType.LIFE_INSURANCE]
        assert life[0].final_amount <= 100_000

    def test_life_health_combined_cap(self, calc):
        """ประกันชีวิต 90,000 + ประกันสุขภาพ 25,000 = 115,000 → cap รวม 100,000"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.LIFE_INSURANCE, 90_000),
            DeductionEntry(DeductionType.HEALTH_INSURANCE, 25_000),
        ]
        result = calc.calculate(entries, 1_000_000, 900_000)
        life = [i for i in result.line_items if i.deduction_type == DeductionType.LIFE_INSURANCE]
        health = [i for i in result.line_items if i.deduction_type == DeductionType.HEALTH_INSURANCE]
        combined = life[0].final_amount + health[0].final_amount
        assert combined <= 100_000

    def test_parent_health_insurance_cap(self, calc):
        """ประกันสุขภาพบิดามารดา 20,000 → cap ที่ 15,000"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.PARENT_HEALTH_INSURANCE, 20_000),
        ]
        result = calc.calculate(entries, 1_000_000, 900_000)
        parent_health = [i for i in result.line_items if i.deduction_type == DeductionType.PARENT_HEALTH_INSURANCE]
        assert parent_health[0].final_amount == 15_000


class TestRetirementGroupCap:
    """กลุ่มเกษียณ — cap 2 ชั้น"""

    def test_within_group_cap(self, calc):
        """RMF 200,000 + PVD 100,000 = 300,000 → ภายในเพดาน 500,000"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.RMF, 200_000),
            DeductionEntry(DeductionType.PVD, 100_000),
        ]
        result = calc.calculate(entries, 2_000_000, 1_900_000)
        rmf = [i for i in result.line_items if i.deduction_type == DeductionType.RMF]
        pvd = [i for i in result.line_items if i.deduction_type == DeductionType.PVD]
        total = rmf[0].final_amount + pvd[0].final_amount
        assert total == 300_000

    def test_exceeds_group_cap(self, calc):
        """RMF 500,000 + PVD 200,000 = 700,000 → cap ที่ 500,000"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.RMF, 500_000),
            DeductionEntry(DeductionType.PVD, 200_000),
        ]
        result = calc.calculate(entries, 5_000_000, 4_900_000)
        retirement_items = [
            i for i in result.line_items
            if i.deduction_type in (DeductionType.RMF, DeductionType.PVD)
        ]
        total = sum(i.final_amount for i in retirement_items)
        assert total == pytest.approx(500_000)

    def test_thai_esg_outside_group(self, calc):
        """Thai ESG ไม่รวมในเพดาน 500,000 ของกลุ่มเกษียณ"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.RMF, 400_000),
            DeductionEntry(DeductionType.PVD, 100_000),
            DeductionEntry(DeductionType.THAI_ESG, 200_000),
        ]
        result = calc.calculate(entries, 3_000_000, 2_900_000)
        retirement_items = [
            i for i in result.line_items
            if i.deduction_type in (DeductionType.RMF, DeductionType.PVD)
        ]
        esg = [i for i in result.line_items if i.deduction_type == DeductionType.THAI_ESG]
        retirement_total = sum(i.final_amount for i in retirement_items)
        assert retirement_total <= 500_000
        assert esg[0].final_amount == 200_000  # Thai ESG independent


class TestDonations:
    """กลุ่ม D: บริจาค — sequential logic"""

    def test_donation_double(self, calc):
        """บริจาค 2 เท่า: จ่าย 50,000 → ลดหย่อน 100,000"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.DONATION_DOUBLE, 50_000),
        ]
        result = calc.calculate(entries, 1_000_000, 900_000)
        dd = [i for i in result.line_items if i.deduction_type == DeductionType.DONATION_DOUBLE]
        # base = 900,000 - 60,000 = 840,000, 10% = 84,000
        # doubled = 100,000, cap at 84,000
        assert dd[0].final_amount == 84_000

    def test_donation_general_uses_reduced_base(self, calc):
        """บริจาคทั่วไป: ใช้ฐานที่หัก donation double แล้ว"""
        entries = [
            DeductionEntry(DeductionType.PERSONAL),
            DeductionEntry(DeductionType.DONATION_DOUBLE, 30_000),
            DeductionEntry(DeductionType.DONATION_GENERAL, 100_000),
        ]
        result = calc.calculate(entries, 1_000_000, 900_000)
        dd = [i for i in result.line_items if i.deduction_type == DeductionType.DONATION_DOUBLE]
        dg = [i for i in result.line_items if i.deduction_type == DeductionType.DONATION_GENERAL]
        # base for dd = 900,000 - 60,000 = 840,000, 10% = 84,000
        # doubled = 60,000 (within cap) → dd = 60,000
        # base for dg = 840,000 - 60,000 = 780,000, 10% = 78,000
        # dg = min(100,000, 78,000) = 78,000
        assert dd[0].final_amount == 60_000
        assert dg[0].final_amount == 78_000
