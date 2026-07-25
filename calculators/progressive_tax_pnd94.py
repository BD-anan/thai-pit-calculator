"""
Progressive Tax Calculator for PND 94 (ภ.ง.ด. 94).
ขั้นบันไดเดียวกับเต็มปี — เปลี่ยนเฉพาะ import config
"""

from dataclasses import dataclass, field

from config.tax_rates_2569_pnd94 import PROGRESSIVE_BRACKETS


@dataclass
class BracketDetail:
    """รายละเอียดภาษีแต่ละขั้น"""
    bracket_lower: float
    bracket_upper: float | None
    rate: float
    taxable_in_bracket: float
    tax_in_bracket: float


@dataclass
class ProgressiveTaxResult:
    """ผลลัพธ์การคำนวณภาษีขั้นบันได"""
    net_income: float
    brackets: list[BracketDetail] = field(default_factory=list)

    @property
    def total_tax(self) -> float:
        return sum(b.tax_in_bracket for b in self.brackets)


class ProgressiveTaxCalculatorPND94:
    """คำนวณภาษีแบบขั้นบันไดสำหรับ ภ.ง.ด. 94"""

    def calculate(self, net_income: float) -> ProgressiveTaxResult:
        result = ProgressiveTaxResult(net_income=net_income)

        if net_income <= 0:
            return result

        remaining = net_income
        prev_upper = 0

        for upper_bound, rate in PROGRESSIVE_BRACKETS:
            if remaining <= 0:
                break

            if upper_bound is None:
                taxable = remaining
            else:
                bracket_size = upper_bound - prev_upper
                taxable = min(remaining, bracket_size)

            tax = taxable * rate

            result.brackets.append(BracketDetail(
                bracket_lower=prev_upper,
                bracket_upper=upper_bound,
                rate=rate,
                taxable_in_bracket=taxable,
                tax_in_bracket=tax,
            ))

            remaining -= taxable
            prev_upper = upper_bound if upper_bound is not None else prev_upper

        return result
