"""
Flat Tax Calculator (ภาษีแบบเหมา 0.5%)
คำนวณภาษีจากเงินได้ที่ไม่ใช่เงินเดือน

Business rules:
- ใช้เมื่อเงินได้นอก 40(1) รวมกัน >= 1,000,000 บาท
- อัตรา 0.5% ของเงินได้ทุกประเภท ยกเว้นเงินเดือน 40(1)
- ถ้าผลลัพธ์ <= 5,000 บาท → ยกเว้นวิธีนี้
"""

from dataclasses import dataclass

from config.tax_rates_2568 import (
    FLAT_TAX_RATE, FLAT_TAX_THRESHOLD, FLAT_TAX_EXEMPTION,
)


@dataclass
class FlatTaxResult:
    """ผลลัพธ์การคำนวณภาษีเหมา"""
    non_salary_income: float
    tax_amount: float
    is_applicable: bool  # ต้องคำนวณวิธีนี้หรือไม่
    is_exempted: bool  # ได้รับยกเว้นเพราะ <= 5,000
    reason: str


class FlatTaxCalculator:
    """คำนวณภาษีแบบเหมา 0.5%"""

    def calculate(self, non_salary_income: float) -> FlatTaxResult:
        """
        Args:
            non_salary_income: เงินได้ทุกประเภทยกเว้น 40(1)
        """
        # Check if flat tax is applicable
        if non_salary_income < FLAT_TAX_THRESHOLD:
            return FlatTaxResult(
                non_salary_income=non_salary_income,
                tax_amount=0,
                is_applicable=False,
                is_exempted=False,
                reason=f"Non-salary income ({non_salary_income:,.0f}) < threshold ({FLAT_TAX_THRESHOLD:,})",
            )

        tax = non_salary_income * FLAT_TAX_RATE

        # Exemption: if tax <= 5,000, exempt this method
        if tax <= FLAT_TAX_EXEMPTION:
            return FlatTaxResult(
                non_salary_income=non_salary_income,
                tax_amount=0,
                is_applicable=True,
                is_exempted=True,
                reason=f"Flat tax ({tax:,.0f}) <= exemption ({FLAT_TAX_EXEMPTION:,})",
            )

        return FlatTaxResult(
            non_salary_income=non_salary_income,
            tax_amount=tax,
            is_applicable=True,
            is_exempted=False,
            reason=f"{non_salary_income:,.0f} x {FLAT_TAX_RATE:.1%} = {tax:,.0f}",
        )
