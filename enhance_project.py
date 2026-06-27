import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import zipfile

BASE = Path('/home/user/olist')
OUT = BASE/'outputs'
FIG = OUT/'figures'
PBI = OUT/'powerbi'

sns.set_theme(style='whitegrid')
master = pd.read_csv(OUT/'master_orders.csv', parse_dates=['order_purchase_timestamp','order_estimated_delivery_date','order_delivered_customer_date'])
scored = pd.read_csv(OUT/'scored_delivered_orders.csv', parse_dates=['order_purchase_timestamp','order_estimated_delivery_date','order_delivered_customer_date'])
kpis = json.loads((OUT/'kpis.json').read_text())
metrics = json.loads((OUT/'model_metrics.json').read_text())
threshold = pd.read_csv(OUT/'threshold_tuning.csv')

master['purchase_date'] = master['order_purchase_timestamp'].dt.date
master['purchase_month'] = master['order_purchase_timestamp'].dt.to_period('M').astype(str)
master['week_day'] = master['order_purchase_timestamp'].dt.day_name()
master['delivery_gap_days'] = pd.to_numeric(master['delivery_gap_days'], errors='coerce')
master['review_score'] = pd.to_numeric(master['review_score'], errors='coerce')
master['total_price'] = pd.to_numeric(master['total_price'], errors='coerce')
master['total_freight'] = pd.to_numeric(master['total_freight'], errors='coerce')
master['payment_value'] = pd.to_numeric(master['payment_value'], errors='coerce')
master['payment_installments_max'] = pd.to_numeric(master['payment_installments_max'], errors='coerce')
master['late_delivery'] = pd.to_numeric(master['late_delivery'], errors='coerce').fillna(0).astype(int)

# Additional business/risk-style visuals
plt.figure(figsize=(10,5))
status = master['order_status'].value_counts().reset_index()
status.columns = ['order_status','count']
sns.barplot(data=status, x='order_status', y='count', color='#4c78a8')
plt.title('Order Status Distribution')
plt.xticks(rotation=35)
plt.tight_layout(); plt.savefig(FIG/'order_status_distribution.png', dpi=200); plt.close()

plt.figure(figsize=(10,5))
weekday = master.groupby('week_day').agg(late_rate=('late_delivery','mean'), orders=('order_id','count')).reindex(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']).reset_index()
sns.barplot(data=weekday, x='week_day', y='late_rate', color='#f58518')
plt.title('Late Delivery Rate by Purchase Weekday')
plt.xticks(rotation=35)
plt.tight_layout(); plt.savefig(FIG/'late_rate_by_weekday.png', dpi=200); plt.close()

plt.figure(figsize=(10,5))
hourly = master.groupby('purchase_hour').agg(late_rate=('late_delivery','mean'), orders=('order_id','count')).reset_index()
sns.lineplot(data=hourly, x='purchase_hour', y='late_rate', marker='o')
plt.title('Late Delivery Rate by Purchase Hour')
plt.tight_layout(); plt.savefig(FIG/'late_rate_by_hour.png', dpi=200); plt.close()

plt.figure(figsize=(10,5))
freight_bin = pd.cut(master['total_freight'], bins=[-1,10,20,30,50,100,500], labels=['0-10','10-20','20-30','30-50','50-100','100+'])
freight_risk = master.groupby(freight_bin, observed=False).agg(late_rate=('late_delivery','mean'), orders=('order_id','count')).reset_index()
sns.barplot(data=freight_risk, x='total_freight', y='late_rate', color='#e45756')
plt.title('Late Delivery Rate by Freight Value Band')
plt.xlabel('Freight Value Band (R$)')
plt.tight_layout(); plt.savefig(FIG/'late_rate_by_freight_band.png', dpi=200); plt.close()

plt.figure(figsize=(10,5))
install = master.groupby('payment_installments_max').agg(orders=('order_id','count'), late_rate=('late_delivery','mean')).reset_index()
install = install[install['payment_installments_max'].between(1,12)]
sns.lineplot(data=install, x='payment_installments_max', y='late_rate', marker='o')
plt.title('Late Delivery Rate by Payment Installments')
plt.xlabel('Installments')
plt.tight_layout(); plt.savefig(FIG/'late_rate_by_installments.png', dpi=200); plt.close()

plt.figure(figsize=(10,5))
rev = master.groupby('review_score').agg(orders=('order_id','count')).reset_index()
sns.barplot(data=rev, x='review_score', y='orders', color='#72b7b2')
plt.title('Review Score Distribution')
plt.tight_layout(); plt.savefig(FIG/'review_score_distribution.png', dpi=200); plt.close()

plt.figure(figsize=(10,5))
risk = scored.copy()
risk['risk_band'] = pd.cut(risk['late_risk_score'], bins=[0,0.2,0.4,0.6,0.8,1.0], labels=['Very Low','Low','Medium','High','Very High'], include_lowest=True)
risk_band = risk.groupby('risk_band', observed=False).agg(orders=('order_id','count')).reset_index()
sns.barplot(data=risk_band, x='risk_band', y='orders', color='#54a24b')
plt.title('Predicted Late-Delivery Risk Distribution')
plt.tight_layout(); plt.savefig(FIG/'risk_score_distribution.png', dpi=200); plt.close()

# confusion matrix at optimal threshold
opt_t = float(metrics['optimal_threshold'])
risk['pred_flag'] = (risk['late_risk_score'] >= opt_t).astype(int)
cm = pd.crosstab(risk['late_delivery'], risk['pred_flag'])
plt.figure(figsize=(5,4))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
plt.title('Confusion Matrix on Delivered Orders')
plt.xlabel('Predicted Late')
plt.ylabel('Actual Late')
plt.tight_layout(); plt.savefig(FIG/'confusion_matrix.png', dpi=200); plt.close()

# threshold business score chart
plt.figure(figsize=(10,5))
sns.lineplot(data=threshold, x='threshold', y='business_score')
plt.axvline(opt_t, linestyle='--', color='red', label=f'Optimal {opt_t:.2f}')
plt.legend()
plt.title('Threshold Tuning by Business Score')
plt.tight_layout(); plt.savefig(FIG/'threshold_tuning_curve.png', dpi=200); plt.close()

# correlation heatmap numeric subset
num_cols = ['item_count','total_price','total_freight','payment_value','payment_installments_max','review_score','delivery_gap_days','late_delivery']
num_df = master[num_cols].copy()
plt.figure(figsize=(8,6))
sns.heatmap(num_df.corr(numeric_only=True), annot=True, cmap='coolwarm', fmt='.2f')
plt.title('Correlation Heatmap')
plt.tight_layout(); plt.savefig(FIG/'correlation_heatmap.png', dpi=200); plt.close()

# KPI summary CSV
summary = pd.DataFrame([
    ['Total Orders', kpis['orders_total']],
    ['Delivered Orders', kpis['delivered_orders']],
    ['Late Deliveries', kpis['late_deliveries']],
    ['Late Rate', round(kpis['late_rate']*100,2)],
    ['Revenue Total', round(kpis['revenue_total'],2)],
    ['Average Order Value', round(kpis['avg_order_value'],2)],
    ['Average Review Score', round(kpis['avg_review_score'],2)],
    ['Average Delivery Days', round(kpis['avg_delivery_days'],2)],
    ['Selected Model', metrics['model_selected']],
    ['Selected ROC-AUC', round(metrics['selected_auc'],3)],
    ['Optimal Threshold', round(metrics['optimal_threshold'],2)],
    ['Optimal Precision', round(metrics['optimal_precision'],3)],
    ['Optimal Recall', round(metrics['optimal_recall'],3)],
], columns=['metric','value'])
summary.to_csv(OUT/'kpi_summary_table.csv', index=False)

# Portfolio README aligned honestly to risk/fraud resume style
readme = f'''# Olist Risk Analytics Project

## Project Positioning
This project uses the **Brazilian E-Commerce Public Dataset by Olist** to demonstrate a risk-analytics workflow aligned with fraud/risk-monitoring resume themes: detection pipeline design, classification modeling, KPI automation, and stakeholder reporting. While the source data is e-commerce logistics data rather than fraud transactions, the operational pattern is highly transferable: identify risky cases early, score them consistently, and surface them in dashboards for faster action.

## Resume-Aligned Framing
This project supports resume narratives such as:
- building end-to-end Python and Scikit-learn risk-scoring pipelines,
- automating KPI dashboards for faster analyst response,
- producing classification outputs and stakeholder-ready risk reports.

## What Was Built
- Multi-table data ingestion and consolidation across orders, customers, sellers, products, payments, and reviews.
- Cleaned master dataset for business analysis.
- Operational EDA focused on delivery-risk behavior.
- Classification model for **late-delivery risk prediction**.
- Threshold tuning for actionability trade-offs.
- Power BI-ready tables and DAX measures.
- Executive dashboard and portfolio-ready reporting.

## Honest Resume Matching
To stay strictly accurate:
- The dataset is **not a fraud dataset**.
- The model predicts **late-delivery risk**, not transaction fraud.
- However, the workflow strongly mirrors fraud-analytics work: feature engineering, classification, threshold tuning, monitoring KPIs, and exception-based reporting.

## Key Results
- Orders analyzed: **{kpis['orders_total']:,}**
- Delivered orders: **{kpis['delivered_orders']:,}**
- Late-delivery rate: **{kpis['late_rate']*100:.1f}%**
- Revenue analyzed: **R$ {kpis['revenue_total']:,.0f}**
- Average review score: **{kpis['avg_review_score']:.2f}**
- Model selected: **{metrics['model_selected']}**
- ROC-AUC: **{metrics['selected_auc']:.3f}**
- Action threshold: **{metrics['optimal_threshold']:.2f}**

## Files
- `outputs/dashboard.html`
- `outputs/Report.md`
- `outputs/Olist_Analysis_Workbook.xlsx`
- `outputs/scored_delivered_orders.csv`
- `outputs/sql/`
- `outputs/powerbi/`
- `outputs/figures/`
- `outputs/Resume_Bullets_and_Interview.md`
'''
(OUT/'Portfolio_README.md').write_text(readme)

# Resume bullets rewritten to match user's style honestly
resume = f'''# Resume-Aligned Bullets Based on the Olist Project

## Honest, Resume-Matched Version
- Built an end-to-end **risk-scoring analytics pipeline** across **99K+ e-commerce orders** using Python, Pandas, and Scikit-learn, engineering multi-table features from payments, fulfillment, product, and geography data to identify orders at elevated delivery risk.
- Reduced manual monitoring effort by preparing **Power BI-ready KPI tables, DAX measures, and automated dashboard assets**, enabling faster analyst review of late-delivery risk, service-level exceptions, and customer experience trends.
- Strengthened operational decision confidence by training and evaluating classification models for **late-delivery prediction** with a measured **ROC-AUC of {metrics['selected_auc']:.3f}**, then tuning alert thresholds to balance intervention coverage and false positives.
- Produced stakeholder-ready risk reports, SQL analysis queries, and visual narratives that connected delivery risk patterns with customer review outcomes, freight burden, geography, and order complexity.

## If You Want a Closer Fraud-Analytics Tone
Use wording like **risk scoring**, **exception monitoring**, **classification pipeline**, **analyst dashboard automation**, and **stakeholder escalation reporting** — but avoid claiming fraud detection on this dataset, because that would not be accurate.

## Interview Talking Points
- Why late-delivery risk was selected as the closest operational analogue to fraud-risk detection.
- How multi-table feature engineering mirrored transaction-monitoring pipelines.
- How threshold tuning supports escalation workflows similar to fraud alert triage.
- How Power BI assets shorten time-to-insight for analysts and managers.
'''
(OUT/'Resume_Bullets_and_Interview.md').write_text(resume)

# Better report with visualization inventory
figs = sorted([p.name for p in FIG.glob('*.png')])
report = (OUT/'Report.md').read_text()
appendix = '\n\n## Visualization Inventory\n' + '\n'.join([f'- `{f}`' for f in figs])
appendix += '\n\n## Analyst Notes\n- This project is framed as risk analytics using a real e-commerce dataset.\n- Claims were kept strictly aligned to actual outputs and metrics.\n'
(OUT/'Report.md').write_text(report + appendix)

# Minimal PDF-style HTML for conversion/download convenience
html_report = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><title>Olist Executive Report</title>
<style>body{{font-family:Arial,sans-serif;max-width:900px;margin:40px auto;padding:20px;color:#222}} h1,h2{{color:#0f172a}} table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #ddd;padding:8px}} .small{{color:#555}}</style></head><body>
<h1>Olist Executive Risk Analytics Report</h1>
<p class="small">Professional analyst package built on the Brazilian E-Commerce Public Dataset by Olist.</p>
<h2>Executive Summary</h2>
<ul>
<li>Total orders: <b>{kpis['orders_total']:,}</b></li>
<li>Delivered orders: <b>{kpis['delivered_orders']:,}</b></li>
<li>Late-delivery rate: <b>{kpis['late_rate']*100:.1f}%</b></li>
<li>Total revenue: <b>R$ {kpis['revenue_total']:,.0f}</b></li>
<li>Average review score: <b>{kpis['avg_review_score']:.2f}</b></li>
<li>Model ROC-AUC: <b>{metrics['selected_auc']:.3f}</b></li>
</ul>
<h2>Resume Alignment</h2>
<p>This project is not fraud detection data, but it demonstrates a highly relevant risk-analytics workflow: feature engineering, classification, threshold tuning, dashboard automation, and escalation-ready reporting.</p>
<h2>Deliverables</h2>
<ul><li>Cleaned master dataset</li><li>EDA and KPI outputs</li><li>Visualization graphs</li><li>Late-delivery prediction model</li><li>Threshold tuning</li><li>SQL query files</li><li>Power BI-ready star schema</li><li>DAX measures</li><li>Excel workbook</li><li>Resume/interview bullets</li></ul>
</body></html>'''
(OUT/'Executive_Report.html').write_text(html_report)

# package fresh zip
zip_path = BASE/'Olist_Ecommerce_Project.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in BASE.rglob('*'):
        if p.is_file() and p.name != zip_path.name:
            z.write(p, p.relative_to(BASE))
print('enhanced and zipped')
print(zip_path)
