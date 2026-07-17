"""
Income models for Thai Personal Income Tax.
ประเภทเงินได้ตามมาตรา 40 แห่งประมวลรัษฎากร
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IncomeType(Enum):
    """ประเภทเงินได้พึงประเมิน ตามมาตรา 40(1)-40(8)"""
    SALARY = "40(1)"             # เงินเดือน ค่าจ้าง โบนัส
    COMMISSION = "40(2)"         # ค่าธรรมเนียม ค่านายหน้า
    ROYALTY = "40(3)"            # ค่าลิขสิทธิ์ ค่า goodwill
    INTEREST_DIVIDEND = "40(4)"  # ดอกเบี้ย เงินปันผล
    RENTAL = "40(5)"             # ค่าเช่าทรัพย์สิน
    PROFESSION = "40(6)"        # วิชาชีพอิสระ
    CONTRACTOR = "40(7)"        # รับเหมา
    OTHER = "40(8)"              # เงินได้อื่นๆ


class FilingStatus(Enum):
    """สถานะการยื่นแบบ"""
    SINGLE = "single"                           # โสด
    MARRIED_FILING_SEPARATELY = "married_sep"   # สมรส แยกยื่น
    # Phase 2:
    MARRIED_FILING_JOINTLY = "married_joint"    # สมรส รวมคำนวณ
    MARRIED_SEPARATE_SALARY = "married_sep_sal" # สมรส แยกเฉพาะ 40(1)


class ExpenseMethod(Enum):
    """วิธีหักค่าใช้จ่าย"""
    FLAT_RATE = "flat_rate"  # หักแบบเหมา
    ACTUAL = "actual"        # หักตามจริง


@dataclass
class IncomeEntry:
    """
    รายการเงินได้แต่ละรายการ

    Attributes:
        income_type: ประเภทเงินได้ 40(1)-40(8)
        amount: จำนวนเงินได้
        sub_type: ประเภทย่อย เช่น "building" สำหรับ 40(5)
                  หรือ "medical" สำหรับ 40(6)
        expense_method: วิธีหักค่าใช้จ่าย (เหมา/ตามจริง)
        actual_expense: ค่าใช้จ่ายตามจริง (ใช้เมื่อ expense_method = ACTUAL)
    """
    income_type: IncomeType
    amount: float
    sub_type: Optional[str] = None
    expense_method: ExpenseMethod = ExpenseMethod.FLAT_RATE
    actual_expense: Optional[float] = None

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Income amount cannot be negative")
        if self.expense_method == ExpenseMethod.ACTUAL and self.actual_expense is None:
            raise ValueError("actual_expense is required when using ACTUAL expense method")


@dataclass
class TaxpayerIncome:
    """
    รวมเงินได้ทั้งหมดของผู้เสียภาษี

    Attributes:
        filing_status: สถานะการยื่นแบบ
        incomes: รายการเงินได้ทั้งหมด
    """
    filing_status: FilingStatus = FilingStatus.SINGLE
    incomes: list[IncomeEntry] = field(default_factory=list)

    def add_income(self, entry: IncomeEntry) -> None:
        self.incomes.append(entry)

    def total_assessable_income(self) -> float:
        """เงินได้พึงประเมินรวมทั้งหมด"""
        return sum(e.amount for e in self.incomes)

    def total_by_type(self, income_type: IncomeType) -> float:
        """เงินได้รวมตามประเภท"""
        return sum(e.amount for e in self.incomes if e.income_type == income_type)

    def total_non_salary(self) -> float:
        """เงินได้รวมที่ไม่ใช่เงินเดือน (สำหรับคำนวณภาษีเหมา)"""
        return sum(
            e.amount for e in self.incomes
            if e.income_type != IncomeType.SALARY
        )

    def entries_by_type(self, income_type: IncomeType) -> list[IncomeEntry]:
        """รายการเงินได้ตามประเภท"""
        return [e for e in self.incomes if e.income_type == income_type]
