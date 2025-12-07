# OpenEMR Patient Import Script

Populates OpenEMR with realistic Vietnamese patient records including demographics, medical history, medications, allergies, encounters, vitals, and lab results.

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
