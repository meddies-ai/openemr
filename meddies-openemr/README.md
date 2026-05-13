# OpenEMR Demo Data — Meddies

Two things live here:

1. **`import_and_enrich.py` + `patients.jsonl`** — 20 realistic Vietnamese patients (demographics, history, meds, allergies, encounters, vitals, labs).
2. **`test-scenarios/`** — 5 D10a stress-test patient bundles (FHIR R4 transaction Bundles), one per agent-eval scenario. Loaded by `meddies-app/scripts/demo-fhir.sh up`.

The fork also carries the `MedicationRequest.dosageInstruction.timing.repeat` patch (`src/Services/FHIR/FhirMedicationRequestService.php`) so structured frequency/period/periodUnit is available to clinical decision support.

## Quick Start

### 1. Run OpenEMR
```bash
git clone https://github.com/openemr/openemr.git
cd openemr/docker/production
docker-compose up -d
```
Wait ~2-3 minutes for OpenEMR to initialize, then access at http://localhost (admin/pass).

### 2. Install Dependencies
```bash
pip3 install requests
```

### 3. Run Import Script
```bash
cd meddies-openemr
python3 import_and_enrich.py
```

## Files

| File | Description |
|------|-------------|
| `import_and_enrich.py` | Main import script - reads JSONL and populates OpenEMR |
| `patients.jsonl` | Patient data - one JSON object per line |

## Configuration

Edit `import_and_enrich.py` if needed:
```python
OPENEMR_URL = "http://localhost"
USERNAME = "admin"
PASSWORD = "pass"
```

## Patient Data (patients.jsonl)

20 Vietnamese patients with diverse conditions, ages (6-84), backgrounds, and locations:

| # | Patient | Age | Key Conditions |
|---|---------|-----|----------------|
| 1 | Nguyễn Thị Xương | 69F | Diabetes, Hypertension, Hyperlipidemia, Osteoarthritis |
| 2 | Trần Văn Trinh | 43M | Bronchitis, GERD, Anxiety |
| 3 | Phạm Khánh Xinh | 22F | Asthma, Allergies, Iron-deficiency Anemia |
| 4 | Lê Đình Hải | 76M | COPD, AFib, Diabetic Nephropathy, CKD, Depression |
| 5 | Võ Thị Hồng Thanh | 34F | Lupus (SLE), Lupus Nephritis, Antiphospholipid Syndrome |
| 6 | Hoàng Quốc Bình | 46M | Chronic Hepatitis B, Fatty Liver, Gout, Obesity |
| 7 | Đặng Thị Mai | 6F | Atopic Dermatitis, Peanut Allergy, Otitis Media, Speech Delay |
| 8 | Bùi Anh Đức | 29M | Major Depression, Insomnia, Tension Headache |
| 9 | Vũ Thị Ngọc Lan | 62F | Breast Cancer (remission), Lymphedema, Neuropathy |
| 10 | Ngô Minh Quang | 24M | Type 1 Diabetes, Celiac Disease, Hashimoto Thyroiditis |
| 11 | Phan Thị Hương | 39F | Pregnancy 28w, Gestational Diabetes, PIH, Anemia |
| 12 | Đinh Văn Tùng | 84M | Alzheimer, Parkinson, CHF, AFib, Hearing Loss |
| 13 | Lý Thị Phương Thảo | 26F | PCOS, Insulin Resistance, Acne, Obesity |
| 14 | Trương Đình Khoa | 52M | CAD s/p CABG, Diabetes, HTN, Sleep Apnea, Obesity |
| 15 | Cao Thị Kim Yến | 10F | ALL (Leukemia, remission), Neutropenia, Growth Delay |
| 16 | Hồ Văn Sơn | 36M | Traumatic Brain Injury, Post-concussion, Epilepsy, Depression |
| 17 | Đỗ Thị Mỹ Linh | 49F | Rheumatoid Arthritis, ILD, Sjögren Syndrome, Osteoporosis |
| 18 | Tạ Văn An | 56M | ESRD on Hemodialysis, Renal Anemia, Hyperparathyroidism |
| 19 | Mai Thị Nga | 32F | HIV (virally suppressed), Anxiety, Lipodystrophy |
| 20 | Lương Minh Phúc | 15M | Autism Spectrum Disorder, ADHD, Sensory Processing, Anxiety |

Each patient includes:
- Demographics, problems (ICD-10), medications, allergies
- Social/family history, insurance
- Multiple encounters with vitals and lab results (LOINC-coded)

## Adding New Patients

Add a new line to `patients.jsonl`:
```json
{"fname": "Name", "lname": "Surname", "DOB": "1990-01-01", "sex": "Male", "problems": [...], "medications": [...], "encounters": [...]}
```

## Test scenarios (`test-scenarios/`)

5 FHIR R4 `transaction` Bundles. Each one mirrors a D10a stress-test scenario; they ship with full `MedicationRequest.dosageInstruction.timing.repeat` structure (frequency/period/periodUnit) since this fork carries the populate-timing patch.

| File | Scenario | Patient | Key clinical context |
|---|---|---|---|
| `01-refill-stable.json` | Routine refill | Phạm Văn An, 70M | Post-MI, stable amlodipine + atorvastatin 2 years; refill request |
| `02-new-med-initiation.json` | New medication | Nguyễn Thị Hoa, 58F | New T2DM dx, HbA1c 7.8, eGFR 88, considering metformin start |
| `03-ckd-dose-change.json` | CKD dose change | Trần Văn Bình, 67M | eGFR declining 45 → 32 over 6 months, on metformin + lisinopril |
| `04-pediatric-dosing.json` | Pediatric dosing | Lê Minh Tuấn, 4yr 18kg | Otitis media, no known allergies, weight parent-reported |
| `05-ddi-quickcheck.json` | DDI quick-check | Vũ Thị Lan, 72F | Chronic amiodarone + warfarin, query about adding azithromycin |

**Patient ID convention:** all scenario patients use the `meddies-test-` prefix to avoid collision with the 20 base patients. Example: `meddies-test-3471`.

**Loading:** automated by `meddies-app/scripts/demo-fhir.sh up`. Each bundle POSTs as a single FHIR transaction to `/apis/default/fhir`. Manual load:
```bash
curl -k -X POST https://localhost/apis/default/fhir \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/fhir+json" \
  --data @test-scenarios/01-refill-stable.json
```

## How It Works

Uses web session authentication (not API) to submit forms:
1. Login → get session cookie
2. Create patient → `/interface/new/new_comprehensive_save.php`
3. Add problems/meds/allergies → `/interface/patient_file/summary/add_edit_issue.php`
4. Create encounters → `/interface/forms/newpatient/save.php`
5. Add vitals → `/interface/forms/vitals/save.php`
6. Add labs → `/interface/forms/observation/save.php`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: requests` | Run `pip3 install requests` |
| Login fails | Check OpenEMR is running at configured URL |
| Patient not found | Search in OpenEMR UI to verify creation |

## Reinstall

```bash
cd ~/openemr/docker/production
docker-compose down -v
docker system prune -a
docker-compose up -d
```
