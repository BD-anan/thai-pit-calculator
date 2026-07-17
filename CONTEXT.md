# Thai Personal Income Tax Calculator — Domain Glossary

This document defines the canonical terms used throughout this codebase.
It is **not** a spec or implementation guide — only a glossary.

## Tax Entities

- **Taxpayer (ผู้มีเงินได้):** A natural person who earns assessable income during a tax year. May file individually or jointly with a spouse.
- **Spouse (คู่สมรส):** A legally married partner whose income may be filed jointly or separately.
- **Filing Status (สถานะการยื่นแบบ):** Determines how a taxpayer's return is processed. Values: Single, Married-Filing-Separately, Married-Filing-Jointly (phase 2), Married-Separate-Salary-Only (phase 2).

## Income (เงินได้พึงประเมิน)

- **Assessable Income (เงินได้พึงประเมิน):** Total income subject to tax under Section 40 of the Revenue Code.
- **Income Type (ประเภทเงินได้):** One of eight categories defined under Section 40(1) through 40(8), each with its own expense deduction rules.
- **Net Income (เงินได้สุทธิ):** Assessable Income minus Expenses minus Allowances. This is the base for progressive tax calculation.

## Expenses (ค่าใช้จ่าย)

- **Expense Deduction (การหักค่าใช้จ่าย):** A deduction applied to assessable income before allowances. Rates vary by Income Type.
- **Shared Expense Cap (เพดานค่าใช้จ่ายร่วม 40(1)+40(2)):** Income Types 40(1) and 40(2) share a combined flat-rate expense deduction of 50%, capped at 100,000 THB total — not 100,000 each.

## Allowances (ค่าลดหย่อน)

- **Allowance (ค่าลดหย่อน):** A deduction from income-after-expenses that reduces Net Income. Each allowance has its own individual cap.
- **Group Cap (เพดานรวมกลุ่ม):** Certain allowances share a combined ceiling. The individual cap is applied first, then the group cap is applied to the sum.
- **Retirement Group (กลุ่มเกษียณ):** Allowances sharing a 500,000 THB combined cap: life-insurance-annuity, PVD, National Savings Fund, GPF, Private Teacher Aid Fund, and RMF.
- **Thai ESG:** Stands alone — not part of the Retirement Group cap.
- **Donation Double (บริจาค 2 เท่า):** Donations to education/sports/public benefit, deductible at 2x actual amount, capped at 10% of income-after-other-allowances. Calculated before General Donation.
- **General Donation (บริจาคทั่วไป):** Deductible at actual amount, capped at 10% of income remaining after Donation Double has been subtracted.

## Tax Calculation

- **Progressive Tax (ภาษีแบบขั้นบันได):** Tax computed by applying graduated rates to Net Income. Always calculated.
- **Flat Tax (ภาษีแบบเหมา):** 0.5% of non-salary assessable income. Calculated only when non-40(1) income totals 1,000,000 THB or more. Exempted if result is ≤ 5,000 THB.
- **Tax Payable (ภาษีที่ต้องชำระ):** The higher of Progressive Tax and Flat Tax (when applicable).

## Separation Tax (Phase 2)

- **Severance Pay Separate Calculation (เงินได้ครั้งเดียวเพราะเหตุออกจากงาน):** A special computation for lump-sum severance that the taxpayer may elect to calculate separately from regular income. Deferred to phase 2.
