# ⚡ ប្រព័ន្ធគ្រប់គ្រងការប្រើប្រាស់អគ្គិសនី និងវិក្កយបត្រ (EDC Electricity Billing System)

ប្រព័ន្ធគ្រប់គ្រងអគ្គិសនី បង្កើតឡើងដោយប្រើប្រាស់ **Python (Flask)**, **SQLite3**, **Modern CSS**, និងគាំទ្រការទូទាត់តាម **Bakong KHQR**។

---

## 🚀 របៀបដំណើការនៅលើកុំព្យូទ័រ (Run Locally)

លោកអ្នកអាចជ្រើសរើសរបៀបដំណើរការបានយ៉ាងងាយស្រួលតាមរយៈ File ខាងក្រោម៖

1. **ដំណើរការបែប App Mode (គ្មានរបារ URL / Address Bar) & បិទ CMD ស្វ័យប្រវត្តិ**៖
   - ចុចបើក File `Run.bat`
2. **ដំណើរការលើ Browser ធម្មតា (មាន Tabs & URL Bar)**៖
   - ចុចបើក File `Run_Browser.bat`
3. **បិទដំណើរការប្រព័ន្ធ**៖
   - ចុចបើក File `Stop.bat`

---

## 🔄 របៀបអាប់ដេត និង Push ទៅកាន់ GitHub (Update & Push to GitHub)

ដើម្បីបញ្ជូនកូដ ឬអាប់ដេតទិន្នន័យទៅកាន់ GitHub Repository [NinjaGPS2/Test_Project](https://github.com/NinjaGPS2/Test_Project)៖

1. គ្រាន់តែចុចពីរដង (Double-click) លើ File **`Push_To_GitHub.bat`**
2. ប្រព័ន្ធនឹងធ្វើការស្វែងរក Git, រៀបចំ Commit និង Push ទៅកាន់ GitHub ដោយស្វ័យប្រវត្តិ
3. បញ្ចូលចំណាំ (Commit Message) ឬចុច **Enter** ដើម្បីប្រើសារលំនាំដើម

---

## 🌐 របៀប Deploy លើ Cloud (ឥតគិតថ្លៃ / Free Hosting)

គម្រោងនេះត្រូវបានរៀបចំឯកសារចាំបាច់រួចជាស្រេចសម្រាប់ Deploy រួមមាន `requirements.txt`, `Procfile`, `runtime.txt`, និង `render.yaml`។

### ជម្រើសទី ១៖ Deploy លើ [Render.com](https://render.com) (ណែនាំបំផុត)
1. បង្កើតគណនី ឬ Login ចូល [Render.com](https://render.com) (ភ្ជាប់ជាមួយ GitHub)
2. ចុច **New +** រួចជ្រើសរើស **Web Service**
3. ជ្រើសរើស Repository **`NinjaGPS2/Test_Project`**
4. កំណត់ Settings៖
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. ចុច **Create Web Service** ជាការស្រេច! ប្រព័ន្ធនឹងបង្កើត Web Link សម្រាប់ប្រើប្រាស់ Online ភ្លាមៗ។

### ជម្រើសទី ២៖ Deploy លើ [Railway.app](https://railway.app)
1. ចូលទៅកាន់ Railway.app ហើយ Login ជាមួយ GitHub
2. ចុច **New Project** -> **Deploy from GitHub repo**
3. ជ្រើសរើស `NinjaGPS2/Test_Project`
4. Railway នឹង Detect `Procfile` និង Deploy ដោយស្វ័យប្រវត្តិ។

---

## 🔐 គណនីចូលប្រើប្រាស់ដំបូង (Default Credentials)

- **Admin Account**: `ADMIN`
- **Password**: `12345@`
- **Role**: Admin (អាចអនុម័តសំណើចុះឈ្មោះអ្នកប្រើប្រាស់ថ្មីៗ, គ្រប់គ្រងអតិថិជន, វិក្កយបត្រ, និងរបាយការណ៍)

---

## 📁 រចនាសម្ព័ន្ធឯកសារ (Project Structure)

```
DAY_3/
├── app.py                  # កម្មវិធីមេ Flask Backend Application & Routes
├── database.py             # គ្រប់គ្រង Database SQLite3 Schema & Seed
├── tariff_engine.py        # ម៉ាស៊ីនគណនាតម្លៃភ្លើងតាមកាំពន្ធគយ (Tariff)
├── khqr_service.py         # បង្កើត Bakong KHQR Payload & QR Codes
├── seed_data.py            # បញ្ចូលទិន្នន័យគំរូ និងអ្នកប្រើប្រាស់
├── requirements.txt        # បញ្ជី Packages សម្រាប់ Run & Deploy
├── Procfile                # កំណត់ Web Server (Gunicorn) សម្រាប់ Cloud Deploy
├── runtime.txt             # កំណត់ជំនាន់ Python 3.11
├── render.yaml             # ការកំណត់ Cloud Blueprint សម្រាប់ Render
├── .gitignore              # បញ្ជី File ដែលមិនត្រូវ Push ទៅ Git
├── Run.bat                 # បើកដំណើរការបែប App Mode គ្មាន URL
├── Run_Browser.bat         # បើកដំណើរការលើ Web Browser ធម្មតា
├── Stop.bat                # បិទដំណើរការ Server
└── Push_To_GitHub.bat      # ឧបករណ៍ Sync & Push ទៅកាន់ GitHub ដោយស្វ័យប្រវត្តិ
```
