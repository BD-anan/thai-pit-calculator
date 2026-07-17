"""
Tests for ProgressiveTaxCalculator.
ทดสอบการคำนวณภาษีแบบขั้นบันได
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from calculators.progressive_tax import ProgressiveTaxCalculator


@pytest.fixture
def calc():
    return ProgressiveTaxCalculator()


class TestProgressiveTax:

    def test_zero_income(self, calc):
        result = calc.calculate(0)
        assert result.total_tax == 0

    def test_below_exemption(self, calc):
        """เงินได้สุทธิ 150,000 → ภาษี 0 (ยกเว้น)"""
        result = calc.calculate(150_000)
        assert result.total_tax == 0

    def test_exactly_150k(self, calc):
        """เงินได้สุทธิ 150,000 → ภาษี 0"""
        result = calc.calculate(150_000)
        assert result.total_tax == 0

    def test_bracket_5pct(self, calc):
        """เงินได้สุทธิ 300,000 → ภาษี 7,500"""
        # (300,000 - 150,000) x 5% = 7,500
        result = calc.calculate(300_000)
        assert result.total_tax == 7_500

    def test_bracket_10pct(self, calc):
        """เงินได้สุทธิ 500,000 → ภาษี 27,500"""
        # 5% bracket: 150,000 x 5% = 7,500
        # 10% bracket: 200,000 x 10% = 20,000
        # Total: 27,500
        result = calc.calculate(500_000)
        assert result.total_tax == 27_500

    def test_bracket_15pct(self, calc):
        """เงินได้สุทธิ 750,000 → ภาษี 65,000"""
        result = calc.calculate(750_000)
        assert result.total_tax == 65_000

    def test_bracket_20pct(self, calc):
        """เงินได้สุทธิ 1,000,000 → ภาษี 115,000"""
        result = calc.calculate(1_000_000)
        assert result.total_tax == 115_000

    def test_bracket_25pct(self, calc):
        """เงินได้สุทธิ 2,000,000 → ภาษี 365,000"""
        result = calc.calculate(2_000_000)
        assert result.total_tax == 365_000

    def test_bracket_30pct(self, calc):
        """เงินได้สุทธิ 5,000,000 → ภาษี 1,265,000"""
        result = calc.calculate(5_000_000)
        assert result.total_tax == 1_265_000

    def test_bracket_35pct(self, calc):
        """เงินได้สุทธิ 10,000,000 → ภาษี 3,015,000"""
        # 1,265,000 + (10,000,000 - 5,000,000) x 35% = 1,265,000 + 1,750,000
        result = calc.calculate(10_000_000)
        assert result.total_tax == 3_015_000

    def test_mid_bracket(self, calc):
        """เงินได้สุทธิ 400,000 → ภาษี 17,500"""
        # 5% bracket: 150,000 x 5% = 7,500
        # 10% bracket: 100,000 x 10% = 10,000
        # Total: 17,500
        result = calc.calculate(400_000)
        assert result.total_tax == 17_500

    def test_negative_income(self, calc):
        """เงินได้สุทธิติดลบ → ภาษี 0"""
        result = calc.calculate(-100_000)
        assert result.total_tax == 0

    def test_bracket_details(self, calc):
        """ตรวจสอบรายละเอียดขั้นบันได"""
        result = calc.calculate(500_000)
        assert len(result.brackets) == 3
        # Bracket 1: 0-150k @ 0%
        assert result.brackets[0].rate == 0.00
        assert result.brackets[0].tax_in_bracket == 0
        # Bracket 2: 150k-300k @ 5%
        assert result.brackets[1].rate == 0.05
        assert result.brackets[1].tax_in_bracket == 7_500
        # Bracket 3: 300k-500k @ 10%
        assert result.brackets[2].rate == 0.10
        assert result.brackets[2].tax_in_bracket == 20_000
