# 🏭 Cement Quality Analytics Dashboard

> **Intelligent quality control analysis for Raw Meal, Clinker (OPC), and Cement data**
>
> Auto-detects material type | Predicts strength | Calculates coating index | Cost impact analysis

---

## 📋 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Usage](#-usage)
- [Supported Data Formats](#-supported-data-formats)
- [Analysis Modules](#-analysis-modules)
- [Screenshots](#-screenshots)
- [Deploy](#-deploy)
- [License](#-license)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🏷️ **Auto-Detection** | Automatically identifies Raw Meal, Clinker, or Cement from column headers |
| 📊 **KPI Dashboard** | Real-time key performance indicators with color-coded status |
| 📈 **Trend Analysis** | Interactive charts with USL/LSL control limits |
| 🔬 **Process Capability** | Cp/Cpk calculations with capability assessment |
| 🎯 **Coating Index** | Kiln ring formation risk prediction |
| 💪 **Strength Prediction** | 28-day compressive strength estimation (Bogue-based) |
| 💰 **Cost Calculator** | Fuel efficiency, raw material waste, and cost impact |
| 📄 **Auto-Report** | Downloadable CSV and text reports with recommendations |

---

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/cement-quality-analytics.git
cd cement-quality-analytics
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install streamlit pandas numpy plotly openpyxl xlrd
```

### Step 3: Run the App

```bash
streamlit run cement_quality_app.py
```

The app will open automatically in your browser at:
```
http://localhost:8501
```

If port 8501 is busy:
```bash
streamlit run cement_quality_app.py --server.port 8502
```

---

## 📖 Usage

### 1. Upload Your Data

Drag and drop your **Excel (.xlsx)** or **CSV (.csv)** file into the sidebar upload area.

### 2. Auto-Detection

The app automatically identifies the material type based on column headers:

| Material | Detected By |
|----------|-------------|
| **Clinker** | C3S, C2S, C3A, C4AF, Liq_phase, F_CaO, LSF, SM, AM |
| **Raw Meal** | LOI, LSF, SM, AM, Moisture, Homogeneity |
| **Cement** | Blaine, Fineness, Setting Time, Compressive Strength |

### 3. Explore 6 Analysis Tabs

After upload, navigate through the tabs:

1. **📊 Overview & KPIs** — Key metrics, data preview, statistics, overall grade
2. **📈 Trends & Control** — Time-series trends with control limits, mineral phase stacked area
3. **🔬 Process Capability** — Cp/Cpk table, capability status, variability analysis
4. **🎯 Coating & Burnability** — Coating index, burnability index, strength prediction
5. **💰 Cost & Operations** — Fuel efficiency, cost impact calculator, temperature correlation
6. **📄 Report & Export** — Download CSV/text reports, actionable recommendations

### 4. Cost Calculator (Tab 5)

Input your operational costs:
- Coal Price ($/ton)
- Limestone Price ($/ton)
- Daily Production (tons)

The app calculates:
- Excess fuel cost from high Free CaO
- Raw material waste from LSF deviation
- Total daily and annual cost impact

---

## 📁 Supported Data Formats

### Clinker Data (Expected Columns)
```
Time, SiO2, Al2O3, Fe2O3, CaO, MgO, K2O, Na2O, SO3, Sum,
LSF, SM, AM, C3S, C2S, C3A, C4AF, Liq_phase, ASR, T_alk,
M_SO3, Excess_SO3, Litre_Weight, F_CaO, Temp, Remarks
```

### Raw Meal Data (Expected Columns)
```
Time, SiO2, Al2O3, Fe2O3, CaO, MgO, K2O, Na2O, SO3, LOI,
LSF, SM, AM, Moisture, Homogeneity_Index
```

### Cement Data (Expected Columns)
```
Time, Blaine, SO3, Setting_Time_Initial, Setting_Time_Final,
Soundness, 3Day_Strength, 7Day_Strength, 28Day_Strength, Fineness
```

> **Note:** Column names are case-insensitive. The app recognizes common aliases like `F-CaO`, `Free CaO`, `Liquid Phase`, etc.

---

## 🔬 Analysis Modules

### Coating Index Formula
```
Coating Index = (Liquid Phase % × C3A / C4AF) / 10
```
| Index | Risk Level |
|-------|-----------|
| < 1.55 | Low — minimal ring formation |
| 1.55 – 1.65 | Moderate — normal monitoring |
| > 1.65 | High — inspect kiln for build-ups |

### 28-Day Strength Prediction (Clinker)
```
Predicted Strength = 35 + (C3S - 45) × 0.85 + (C2S - 25) × 0.25
                     + (C3A - 7) × 0.5 - max(0, F_CaO - 1) × 3
                     + (LSF - 90) × 0.3
```

### Process Capability (Cp/Cpk)
| Cpk | Status | Action |
|-----|--------|--------|
| ≥ 1.33 | Excellent | Maintain current process |
| ≥ 1.00 | Capable | Acceptable, monitor trends |
| ≥ 0.67 | Marginal | Investigate and improve |
| < 0.67 | Poor | Immediate corrective action |

---

## 📸 Screenshots

### Overview Dashboard
![Overview](screenshots/overview.png)

### Trends with Control Limits
![Trends](screenshots/trends.png)

### Process Capability
![Capability](screenshots/capability.png)

### Coating Index & Strength
![Coating](screenshots/coating.png)

### Cost Calculator
![Cost](screenshots/cost.png)

---

## 🌐 Deploy

### Deploy on Streamlit Cloud (Free)

1. Push this repository to **GitHub**
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Select your repository
5. Click **Deploy**

Your app will be live with a public URL like:
```
https://your-app-name.streamlit.app
```

### Deploy on Your Server

```bash
# Run in background
nohup streamlit run cement_quality_app.py --server.port 8501 &

# Or use systemd service
```

---

## 🛠️ Development

### Project Structure
```
cement-quality-analytics/
├── cement_quality_app.py      # Main Streamlit application
├── requirements.txt           # Python dependencies
├── sample_clinker_data.csv    # Sample test data
├── README.md                  # This file
├── screenshots/               # App screenshots
└── .gitignore                 # Git ignore rules
```

### Adding New Features

To add a new analysis module:
1. Add calculation functions in `cement_quality_app.py`
2. Create a new tab in the `st.tabs()` section
3. Add visualization using Plotly or Streamlit native charts

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| `streamlit: command not found` | Reinstall: `pip install --upgrade streamlit` |
| Port 8501 already in use | Use `--server.port 8502` or any free port |
| Excel file won't load | Install: `pip install openpyxl xlrd` |
| Browser doesn't open | Manually visit `http://localhost:8501` |
| App crashes on upload | Check column headers match expected format |
| Material not detected | Ensure key columns (C3S, LSF, Blaine) are present |

---

## 📄 License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 FAUJI CEMENT COMPANY LIMITED

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## 👥 Authors & Contact

- **Quality Control Department** — FAUJI CEMENT COMPANY LIMITED (NIZAMPUR)
- **Document:** QC-R-18
- **For support:** Contact your plant QC team or IT department

---

<div align="center">

### 🏭 Built for Cement Quality Excellence

*Automate your QC analysis. Predict strength. Optimize costs. Prevent kiln issues.*

</div>
