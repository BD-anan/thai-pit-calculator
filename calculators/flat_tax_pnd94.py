"""
Flat Tax Calculator for PND 94 (ภ.ง.ด. 94).
ภาษีเหมา 0.5% — threshold ไม่เปลี่ยน, ใช้รายได้ทั้งหมด (ไม่แยกเงินเดือน)

Business rules:
- PND94 มีเฉพาะ 40(5)-40(8) ซึ่งทั้งหมดเป็น non-salary
- threshold 1,000,000 (ไม่หาร เพราะรายได้ที่ยื่นเป็นรายได้ครึ่งปีอยู่แล้ว)
- ภาษีเหมา <= 5,000 → ยกเว้น
"""

from dataclasses import dataclass

from config.tax_rates_2569_pnd94 import (
    FLAT_TAX_RATE, FLAT_TAX_THRESHOLD, FLAT_TAX_EXEMPTION,
)


@dataclass
class FlatTaxResult:
    """ผลลัพธ์การคำนวณภาษีเหมา"""
    total_income: float
    tax_amount: float
    is_applicable: bool
    is_exempted: bool
    reason: str


class FlatTaxCalculatorPND94:
    """คำนวณภาษีเหมา 0.5% สำหรับ ภ.ง.ด. 94"""

    def calculate(self, total_income: float) -> FlatTaxResult:
        """
        Args:
            total_income: เงินได้รวมทั้งหมด 40(5)-40(8)
                          (PND94 ไม่มี 40(1) จึงใช้ทั้งหมด)
        """
        if total_income < FLAT_TAX_THRESHOLD:
            return FlatTaxResult(
                total_income=total_income,
                tax_amount=0,
                is_applicable=False,
                is_exempted=False,
                reason=f"Total income ({total_income:,.0f}) < threshold ({FLAT_TAX_THRESHOLD:,})",
            )

        tax = total_income * FLAT_TAX_RATE

        if tax <= FLAT_TAX_EXEMPTION:
            return FlatTaxResult(
                total_income=total_income,
                tax_amount=0,
                is_applicable=True,
                is_exempted=True,
                reason=f"Flat tax ({tax:,.0f}) <= exemption ({FLAT_TAX_EXEMPTION:,})",
            )

        return FlatTaxResult(
            total_income=total_income,
            tax_amount=tax,
            is_applicable=True,
            is_exempted=False,
            reason=f"{total_income:,.0f} x {FLAT_TAX_RATE:.1%} = {tax:,.0f}",
        )
