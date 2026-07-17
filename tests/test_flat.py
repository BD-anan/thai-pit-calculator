"""
Tests for FlatTaxCalculator.
ทดสอบการคำนวณภาษีแบบเหมา 0.5%
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from calculators.flat_tax import FlatTaxCalculator


@pytest.fixture
def calc():
    return FlatTaxCalculator()


class TestFlatTax:

    def test_below_threshold(self, calc):
        """เงินได้นอก 40(1) < 1,000,000 → ไม่ต้องคำนวณ"""
        result = calc.calculate(500_000)
        assert result.is_applicable is False
        assert result.tax_amount == 0

    def test_at_threshold(self, calc):
        """เงินได้นอก 40(1) = 1,000,000 → ภาษี 5,000 → ยกเว้น"""
        result = calc.calculate(1_000_000)
        assert result.is_applicable is True
        assert result.is_exempted is True
        assert result.tax_amount == 0

    def test_just_above_exemption(self, calc):
        """เงินได้ 1,000,001 → ภาษี 5,000.005 → ไม่ยกเว้น"""
        result = calc.calculate(1_000_001)
        assert result.is_applicable is True
        assert result.is_exempted is False
        assert result.tax_amount == pytest.approx(5_000.005)

    def test_large_income(self, calc):
        """เงินได้ 5,000,000 → ภาษี 25,000"""
        result = calc.calculate(5_000_000)
        assert result.is_applicable is True
        assert result.is_exempted is False
        assert result.tax_amount == 25_000

    def test_zero_income(self, calc):
        """เงินได้ 0 → ไม่ต้องคำนวณ"""
        result = calc.calculate(0)
        assert result.is_applicable is False
