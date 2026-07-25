"""
Deduction models for Thai Personal Income Tax.
ค่าลดหย่อนภาษีเงินได้บุคคลธรรมดา
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DeductionGroup(Enum):
    """กลุ่มค่าลดหย่อน"""
    PERSONAL = "personal"          # กลุ่ม A: ส่วนตัวและครอบครัว
    INSURANCE_SAVING = "insurance"  # กลุ่ม B: ประกันและการออม
    STIMULUS = "stimulus"          # กลุ่ม C: กระตุ้นเศรษฐกิจ
    DONATION = "donation"          # กลุ่ม D: บริจาค


class DeductionType(Enum):
    """ประเภทค่าลดหย่อน"""
    # Group A: ส่วนตัวและครอบครัว
    PERSONAL = "personal"
    SPOUSE = "spouse"
    CHILD = "child"
    CHILD_BORN_2018_PLUS = "child_2018"
    PREGNANCY = "pregnancy"
    PARENT = "parent"
    DISABLED_PERSON = "disabled"

    # Group B: ประกันและการออม
    LIFE_INSURANCE = "life_insurance"
    HEALTH_INSURANCE = "health_insurance"
    PARENT_HEALTH_INSURANCE = "parent_health_insurance"
    LIFE_INSURANCE_ANNUITY = "annuity"
    PVD = "pvd"
    NATIONAL_SAVINGS_FUND = "nsf"       # กอช.
    GPF = "gpf"                          # กบข.
    PRIVATE_TEACHER_FUND = "teacher_fund"
    RMF = "rmf"
    THAI_ESG = "thai_esg"
    SOCIAL_SECURITY = "social_security"

    # Group C: กระตุ้นเศรษฐกิจ
    EASY_E_RECEIPT = "easy_e_receipt"
    HOME_LOAN_INTEREST = "home_loan_interest"
    NEW_HOME_CONSTRUCTION = "new_home"
    VISUAL_ART = "visual_art"
    SOLAR_ROOFTOP = "solar_rooftop"            # Solar Rooftop 2569-2571
    SOCIAL_ENTERPRISE = "social_enterprise"    # วิสาหกิจเพื่อสังคม
    ENERGY_SAVING = "energy_saving"            # ฉลากประหยัดไฟฟ้า 5 ดาว
    CCTV = "cctv"                              # กล้องวงจรปิด เขตพัฒนาพิเศษ

    # Group B (cont.): Thai ESGX — สับเปลี่ยนจาก LTF (2569+)
    THAI_ESGX = "thai_esgx"

    # Group D: บริจาค
    DONATION_DOUBLE = "donation_double"
    DONATION_GENERAL = "donation_general"
    POLITICAL_PARTY = "political_party"


# Mapping: which deduction types belong to the retirement group cap
RETIREMENT_GROUP_TYPES = {
    DeductionType.LIFE_INSURANCE_ANNUITY,
    DeductionType.PVD,
    DeductionType.NATIONAL_SAVINGS_FUND,
    DeductionType.GPF,
    DeductionType.PRIVATE_TEACHER_FUND,
    DeductionType.RMF,
}

# PND94-specific retirement group: only annuity + RMF + กอช.
# (no PVD, กบข., กองทุนครูเอกชน — those are for 40(1) only)
RETIREMENT_GROUP_TYPES_PND94 = {
    DeductionType.LIFE_INSURANCE_ANNUITY,
    DeductionType.RMF,
    DeductionType.NATIONAL_SAVINGS_FUND,
}

# Mapping: deduction type → group
DEDUCTION_GROUP_MAP = {
    DeductionType.PERSONAL: DeductionGroup.PERSONAL,
    DeductionType.SPOUSE: DeductionGroup.PERSONAL,
    DeductionType.CHILD: DeductionGroup.PERSONAL,
    DeductionType.CHILD_BORN_2018_PLUS: DeductionGroup.PERSONAL,
    DeductionType.PREGNANCY: DeductionGroup.PERSONAL,
    DeductionType.PARENT: DeductionGroup.PERSONAL,
    DeductionType.DISABLED_PERSON: DeductionGroup.PERSONAL,
    DeductionType.LIFE_INSURANCE: DeductionGroup.INSURANCE_SAVING,
    DeductionType.HEALTH_INSURANCE: DeductionGroup.INSURANCE_SAVING,
    DeductionType.PARENT_HEALTH_INSURANCE: DeductionGroup.INSURANCE_SAVING,
    DeductionType.LIFE_INSURANCE_ANNUITY: DeductionGroup.INSURANCE_SAVING,
    DeductionType.PVD: DeductionGroup.INSURANCE_SAVING,
    DeductionType.NATIONAL_SAVINGS_FUND: DeductionGroup.INSURANCE_SAVING,
    DeductionType.GPF: DeductionGroup.INSURANCE_SAVING,
    DeductionType.PRIVATE_TEACHER_FUND: DeductionGroup.INSURANCE_SAVING,
    DeductionType.RMF: DeductionGroup.INSURANCE_SAVING,
    DeductionType.THAI_ESG: DeductionGroup.INSURANCE_SAVING,
    DeductionType.THAI_ESGX: DeductionGroup.INSURANCE_SAVING,
    DeductionType.SOCIAL_SECURITY: DeductionGroup.INSURANCE_SAVING,
    DeductionType.EASY_E_RECEIPT: DeductionGroup.STIMULUS,
    DeductionType.HOME_LOAN_INTEREST: DeductionGroup.STIMULUS,
    DeductionType.NEW_HOME_CONSTRUCTION: DeductionGroup.STIMULUS,
    DeductionType.VISUAL_ART: DeductionGroup.STIMULUS,
    DeductionType.SOLAR_ROOFTOP: DeductionGroup.STIMULUS,
    DeductionType.SOCIAL_ENTERPRISE: DeductionGroup.STIMULUS,
    DeductionType.ENERGY_SAVING: DeductionGroup.STIMULUS,
    DeductionType.CCTV: DeductionGroup.STIMULUS,
    DeductionType.DONATION_DOUBLE: DeductionGroup.DONATION,
    DeductionType.DONATION_GENERAL: DeductionGroup.DONATION,
    DeductionType.POLITICAL_PARTY: DeductionGroup.DONATION,
}


@dataclass
class DeductionEntry:
    """
    รายการค่าลดหย่อนแต่ละรายการ

    Attributes:
        deduction_type: ประเภทค่าลดหย่อน
        actual_amount: จำนวนเงินที่จ่ายจริง
        count: จำนวน (เช่น จำนวนบุตร จำนวนบิดามารดา)
    """
    deduction_type: DeductionType
    actual_amount: float = 0.0
    count: int = 1

    def __post_init__(self):
        if self.actual_amount < 0:
            raise ValueError("Deduction amount cannot be negative")


@dataclass
class DeductionLineItem:
    """
    ผลลัพธ์การคำนวณค่าลดหย่อนแต่ละรายการ (หลัง cap)

    Attributes:
        deduction_type: ประเภทค่าลดหย่อน
        claimed_amount: จำนวนที่ขอลดหย่อน (ก่อน cap)
        allowed_amount: จำนวนที่ได้รับอนุญาต (หลัง individual cap)
        final_amount: จำนวนสุดท้าย (หลัง group cap)
        cap_applied: เพดานที่ถูกใช้ (ถ้ามี)
        notes: หมายเหตุ
    """
    deduction_type: DeductionType
    claimed_amount: float
    allowed_amount: float
    final_amount: float
    cap_applied: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class DeductionResult:
    """
    ผลรวมค่าลดหย่อนทั้งหมด

    Attributes:
        line_items: รายละเอียดแต่ละรายการ
        total_deductions: ค่าลดหย่อนรวมทั้งหมด
    """
    line_items: list[DeductionLineItem] = field(default_factory=list)

    @property
    def total_deductions(self) -> float:
        return sum(item.final_amount for item in self.line_items)

    def by_group(self, group: DeductionGroup) -> list[DeductionLineItem]:
        return [
            item for item in self.line_items
            if DEDUCTION_GROUP_MAP.get(item.deduction_type) == group
        ]
