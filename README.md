# Thai Personal Income Tax Calculator (ภาษีเงินได้บุคคลธรรมดา)

โปรแกรมคำนวณภาษีเงินได้บุคคลธรรมดา ปีภาษี 2568 (2025) ตามประมวลรัษฎากร

สร้างขึ้นเพื่อเป็น **open-source reference** ให้ผู้ที่สนใจเรียนรู้ logic การคำนวณภาษี และนำไปต่อยอดเป็น web app, API, หรือ port เป็นภาษาอื่นได้

## โครงสร้างโปรเจกต์

```
thai-pit-calculator/
├── config/
│   └── tax_rates_2568.py        # อัตราภาษี, เพดานค่าลดหย่อน (data-driven)
├── models/
│   ├── income.py                # ประเภทเงินได้ 40(1)-40(8), FilingStatus
│   └── deductions.py            # ประเภทค่าลดหย่อน, group cap definitions
├── calculators/
│   ├── expense_calculator.py    # หักค่าใช้จ่ายตามประเภทเงินได้
│   ├── deduction_calculator.py  # คำนวณค่าลดหย่อน + เพดานรวม
│   ├── progressive_tax.py       # ภาษีแบบขั้นบันได
│   ├── flat_tax.py              # ภาษีแบบเหมา 0.5%
│   └── tax_comparator.py        # เปรียบเทียบ 2 วิธี
├── tests/                       # Unit tests + E2E tests
├── main.py                      # Orchestrator + CLI output
├── CONTEXT.md                   # Domain glossary
└── README.md
```

## วิธีใช้

```bash
# รันตัวอย่าง
python main.py

# รัน tests
pytest tests/ -v
```

## Pipeline การคำนวณ

```
เงินได้ (8 ประเภท)
  │
  ├─ หักค่าใช้จ่าย (ตามประเภท, 40(1)+40(2) cap ร่วม)
  │  = เงินได้หลังหักค่าใช้จ่าย
  │
  ├─ หักค่าลดหย่อน (cap เฉพาะตัว → cap รวมกลุ่ม → บริจาค sequential)
  │  = เงินได้สุทธิ
  │
  ├─ คำนวณภาษีขั้นบันได (0% → 5% → 10% → 15% → 20% → 25% → 30% → 35%)
  │
  ├─ คำนวณภาษีเหมา 0.5% (ถ้า non-salary >= 1M)
  │
  └─ เปรียบเทียบ → เอาตัวที่สูงกว่า = ภาษีที่ต้องชำระ
```

## Business Rules สำคัญ

- **40(1) + 40(2) ใช้เพดานค่าใช้จ่ายร่วมกัน** — เหมา 50% รวมไม่เกิน 100,000 บาท
- **ประกันชีวิต + ประกันสุขภาพ** — รวมไม่เกิน 100,000 บาท
- **กลุ่มเกษียณ** — cap 2 ชั้น: individual cap ก่อน แล้ว group cap 500,000
- **Thai ESG** — แยกวงจากกลุ่มเกษียณ
- **บริจาค** — คิด 2 เท่าก่อน → ทั่วไปคิดจากฐานที่เหลือ (sequential)
- **ภาษีเหมา** — ยกเว้นถ้าผลลัพธ์ <= 5,000 บาท

## Phase 2 (TODO)

- เงินได้ครั้งเดียวเพราะเหตุออกจากงาน (แยกคำนวณ)
- สมรสรวมคำนวณภาษี
- สมรสแยกเฉพาะ 40(1)

## อ้างอิง

- [กรมสรรพากร — แบบ ภ.ง.ด.90 ปี 2568](https://www.rd.go.th/67335.html)
- [Finnomena — สรุปวิธีคำนวณภาษี 2568](https://www.finnomena.com/finnomenafunds/tax-computation-guide/)

## License

MIT — ใช้ แก้ไข แจกจ่ายได้อิสระ
