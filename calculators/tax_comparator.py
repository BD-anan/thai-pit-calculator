"""
Tax Comparator.
เปรียบเทียบภาษีจาก 2 วิธี เอาตัวที่สูงกว่า

Business rule:
- ถ้าต้องคำนวณทั้ง 2 วิธี → เสียภาษีตามวิธีที่สูงกว่า
- ถ้าวิธีเหมาไม่ applicable → ใช้วิธีขั้นบันไดอย่างเดียว
"""

from dataclasses import dataclass

from .progressive_tax import ProgressiveTaxResult
from .flat_tax import FlatTaxResult


@dataclass
class TaxComparisonResult:
    """ผลลัพธ์การเปรียบเทียบภาษี"""
    progressive_result: ProgressiveTaxResult
    flat_result: FlatTaxResult
    chosen_method: str  # "progressive" or "flat"
    tax_payable: float
    explanation: str


class TaxComparator:
    """เปรียบเทียบภาษี 2 วิธี"""

    def compare(
        self,
        progressive_result: ProgressiveTaxResult,
        flat_result: FlatTaxResult,
    ) -> TaxComparisonResult:

        progressive_tax = progressive_result.total_tax
        flat_tax = flat_result.tax_amount

        # If flat tax is not applicable or exempted, use progressive only
        if not flat_result.is_applicable or flat_result.is_exempted:
            return TaxComparisonResult(
                progressive_result=progressive_result,
                flat_result=flat_result,
                chosen_method="progressive",
                tax_payable=progressive_tax,
                explanation=(
                    f"Flat tax not applicable ({flat_result.reason}). "
                    f"Using progressive: {progressive_tax:,.0f} THB"
                ),
            )

        # Both methods applicable — use the higher amount
        if progressive_tax >= flat_tax:
            return TaxComparisonResult(
                progressive_result=progressive_result,
                flat_result=flat_result,
                chosen_method="progressive",
                tax_payable=progressive_tax,
                explanation=(
                    f"Progressive ({progressive_tax:,.0f}) >= "
                    f"Flat ({flat_tax:,.0f}). Using progressive."
                ),
            )
        else:
            return TaxComparisonResult(
                progressive_result=progressive_result,
                flat_result=flat_result,
                chosen_method="flat",
                tax_payable=flat_tax,
                explanation=(
                    f"Flat ({flat_tax:,.0f}) > "
                    f"Progressive ({progressive_tax:,.0f}). Using flat."
                ),
            )
