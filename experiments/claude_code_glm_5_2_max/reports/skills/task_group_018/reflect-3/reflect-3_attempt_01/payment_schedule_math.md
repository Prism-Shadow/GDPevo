# Payment Schedule Math Reference

## Input Parameters

| Parameter | Source |
|---|---|
| `total_due` | fines_and_costs + restitution (per policy application order) |
| `installment_amount` | Approved/requested monthly amount, must be within policy min–max |
| `first_due_days` | From jurisdiction payment policy |
| `return_to_court_offset_days` | From jurisdiction payment policy |
| `submitted_date` | Petition submitted date |
| `account_fee` | From policy; may be $0 (excluded) |

## Computations

### Installment Count
```
full_payment_count = floor(total_due / installment_amount)
final_payment_amount = total_due - (full_payment_count * installment_amount)
```

If `final_payment_amount > 0`:
```
total_installments = full_payment_count + 1
```

If `final_payment_amount == 0` (total divides evenly):
```
final_payment_amount = installment_amount
total_installments = full_payment_count
```

### Dates
```
first_due_date = submitted_date + first_due_days (calendar days)

final_due_date = first_due_date + (total_installments - 1) months
  (same day-of-month as first_due_date; adjust for month-end)

return_to_court_date = final_due_date + return_to_court_offset_days (calendar days)
```

### Example 1: VA-PET-884A (Lena Walsh)
- total_due = 1435.00, installment = 85.00
- full_payment_count = floor(1435/85) = 16 (16 × 85 = 1360)
- final_payment_amount = 1435 - 1360 = 75.00
- total_installments = 17
- first_due_date = 2025-03-12 + 30 days = 2025-04-11
- final_due_date = 2025-04-11 + 16 months = 2026-08-11
- return_to_court_date = 2026-08-11 + 60 days = 2026-10-10

### Example 2: VA-PET-913A (Marcus Hill)
- total_due = 1540.00 (1180 fines+costs + 360 restitution), installment = 50.00
- full_payment_count = floor(1540/50) = 30 (30 × 50 = 1500)
- final_payment_amount = 1540 - 1500 = 40.00
- total_installments = 31
- first_due_date = 2025-03-18 + 30 days = 2025-04-17 (using Gloucester first_due_days=30)
  Wait: 2025-03-18 + 30 = 2025-04-17. ✓
- final_due_date = 2025-04-17 + 30 months = 2027-10-17
- return_to_court_date = 2027-10-17 + 60 days = 2027-12-16

### Example 3: OR26-TR-1188 (Sarah Benton)
- amount_due = 1155.00 (1150 fine + 5 surcharge), monthly = 50.00
- full_payment_count = floor(1155/50) = 23 (23 × 50 = 1150)
- final_payment_amount = 1155 - 1150 = 5.00
- total_installments = 24
- first_due_date = 2026-12-15 (from hearing minutes)
- final_due_date = 2026-12-15 + 23 months = 2027-11-15

### Example 4: OR26-TR-1194 (Jonah Merritt)
- amount_due = 445.00 (440 fine + 5 surcharge), monthly = 55.00
- full_payment_count = floor(445/55) = 8 (8 × 55 = 440)
- final_payment_amount = 445 - 440 = 5.00
- total_installments = 9
- first_due_date = 2026-12-15
- final_due_date = 2026-12-15 + 8 months = 2027-08-15
