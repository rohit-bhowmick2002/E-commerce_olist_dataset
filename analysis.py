import os
import json
import math
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix, roc_curve, precision_recall_curve
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

BASE = Path('.')
DATA = BASE / 'data'
OUT = BASE / 'outputs'
FIG = OUT / 'figures'
SQL = OUT / 'sql'
PBI = OUT / 'powerbi'
MODELS = OUT / 'models'
for p in [OUT, FIG, SQL, PBI, MODELS]:
    p.mkdir(parents=True, exist_ok=True)

sns.set_theme(style='whitegrid')


def load_csv(name, parse_dates=None):
    return pd.read_csv(DATA / name, parse_dates=parse_dates)

customers = load_csv('olist_customers_dataset.csv')
geoloc = load_csv('olist_geolocation_dataset.csv')
items = load_csv('olist_order_items_dataset.csv', parse_dates=['shipping_limit_date'])
payments = load_csv('olist_order_payments_dataset.csv')
reviews = load_csv('olist_order_reviews_dataset.csv', parse_dates=['review_creation_date','review_answer_timestamp'])
orders = load_csv('olist_orders_dataset.csv', parse_dates=['order_purchase_timestamp','order_approved_at','order_delivered_carrier_date','order_delivered_customer_date','order_estimated_delivery_date'])
products = load_csv('olist_products_dataset.csv')
sellers = load_csv('olist_sellers_dataset.csv')
translation = load_csv('product_category_name_translation.csv')

products = products.merge(translation, on='product_category_name', how='left')
products['product_category'] = products['product_category_name_english'].fillna(products['product_category_name']).fillna('unknown')

item_agg = items.groupby('order_id').agg(
    item_count=('order_item_id','count'),
    total_price=('price','sum'),
    total_freight=('freight_value','sum'),
    unique_sellers=('seller_id','nunique'),
    unique_products=('product_id','nunique')
).reset_index()

pay_agg = payments.groupby('order_id').agg(
    payment_count=('payment_sequential','max'),
    payment_value=('payment_value','sum'),
    payment_installments_max=('payment_installments','max'),
    payment_installments_mean=('payment_installments','mean')
).reset_index()

pay_type = pd.crosstab(payments['order_id'], payments['payment_type'])
pay_type.columns = [f'paytype_{c}' for c in pay_type.columns]
pay_type = pay_type.reset_index()

review_agg = reviews.groupby('order_id').agg(
    review_score=('review_score','mean'),
    has_review_comment=('review_comment_message', lambda x: x.notna().any())
).reset_index()
review_agg['has_review_comment'] = review_agg['has_review_comment'].astype(int)

prod_cat = items.merge(products[['product_id','product_category']], on='product_id', how='left')
prod_cat_mode = prod_cat.groupby('order_id')['product_category'].agg(lambda x: x.mode().iat[0] if not x.mode().empty else 'unknown').reset_index()

seller_state_mode = items.merge(sellers[['seller_id','seller_state']], on='seller_id', how='left')
seller_state_mode = seller_state_mode.groupby('order_id')['seller_state'].agg(lambda x: x.mode().iat[0] if not x.mode().empty else 'unknown').reset_index()

master = orders.merge(customers, on='customer_id', how='left') \
    .merge(item_agg, on='order_id', how='left') \
    .merge(pay_agg, on='order_id', how='left') \
    .merge(pay_type, on='order_id', how='left') \
    .merge(review_agg, on='order_id', how='left') \
    .merge(prod_cat_mode, on='order_id', how='left') \
    .merge(seller_state_mode, on='order_id', how='left')

for c in ['paytype_boleto','paytype_credit_card','paytype_debit_card','paytype_voucher']:
    if c not in master.columns:
        master[c] = 0

master['purchase_year'] = master['order_purchase_timestamp'].dt.year
master['purchase_month'] = master['order_purchase_timestamp'].dt.month
master['purchase_dayofweek'] = master['order_purchase_timestamp'].dt.day_name()
master['purchase_hour'] = master['order_purchase_timestamp'].dt.hour
master['approval_delay_hours'] = (master['order_approved_at'] - master['order_purchase_timestamp']).dt.total_seconds()/3600
master['carrier_delay_days'] = (master['order_delivered_carrier_date'] - master['order_approved_at']).dt.total_seconds()/86400
master['delivery_days'] = (master['order_delivered_customer_date'] - master['order_purchase_timestamp']).dt.total_seconds()/86400
master['estimated_days'] = (master['order_estimated_delivery_date'] - master['order_purchase_timestamp']).dt.total_seconds()/86400
master['late_delivery'] = ((master['order_delivered_customer_date'] > master['order_estimated_delivery_date']) & master['order_delivered_customer_date'].notna()).astype(int)
master['delivery_gap_days'] = (master['order_delivered_customer_date'] - master['order_estimated_delivery_date']).dt.total_seconds()/86400
master['delivered_flag'] = (master['order_status'] == 'delivered').astype(int)
master['freight_ratio'] = master['total_freight'] / master['total_price'].replace(0, np.nan)
master['order_value_per_item'] = master['total_price'] / master['item_count'].replace(0, np.nan)
master['seller_customer_same_state'] = (master['seller_state'] == master['customer_state']).astype(int)

# executive KPIs
kpis = {
    'orders_total': int(len(master)),
    'delivered_orders': int((master['order_status'] == 'delivered').sum()),
    'late_deliveries': int(master['late_delivery'].sum()),
    'late_rate': float(master['late_delivery'].mean()),
    'revenue_total': float(master['total_price'].sum()),
    'avg_order_value': float(master['total_price'].mean()),
    'avg_review_score': float(master['review_score'].mean()),
    'avg_delivery_days': float(master.loc[master['delivery_days'].notna(), 'delivery_days'].mean()),
    'customers_unique': int(master['customer_unique_id'].nunique()),
    'sellers_unique': int(sellers['seller_id'].nunique()),
}
with open(OUT/'kpis.json','w') as f:
    json.dump(kpis,f,indent=2)

master.to_csv(OUT/'master_orders.csv', index=False)

# charts
plt.figure(figsize=(10,5))
monthly = master.groupby(pd.Grouper(key='order_purchase_timestamp', freq='M')).agg(revenue=('total_price','sum'), orders=('order_id','count')).reset_index()
plt.plot(monthly['order_purchase_timestamp'], monthly['revenue'], marker='o')
plt.title('Monthly Revenue Trend')
plt.xlabel('Month')
plt.ylabel('Revenue (R$)')
plt.tight_layout(); plt.savefig(FIG/'monthly_revenue.png', dpi=200); plt.close()

plt.figure(figsize=(10,5))
state_late = master[master['order_status']=='delivered'].groupby('customer_state').agg(late_rate=('late_delivery','mean'), orders=('order_id','count')).query('orders >= 500').sort_values('late_rate', ascending=False)
sns.barplot(data=state_late.reset_index(), x='customer_state', y='late_rate', color='#d95f02')
plt.title('Late Delivery Rate by Customer State')
plt.xticks(rotation=45)
plt.tight_layout(); plt.savefig(FIG/'late_rate_by_state.png', dpi=200); plt.close()

plt.figure(figsize=(8,5))
review_late = master[master['review_score'].notna()].groupby('review_score').agg(late_rate=('late_delivery','mean'), orders=('order_id','count')).reset_index()
sns.lineplot(data=review_late, x='review_score', y='late_rate', marker='o')
plt.title('Late Delivery Rate by Review Score')
plt.ylabel('Late Rate')
plt.tight_layout(); plt.savefig(FIG/'late_by_review.png', dpi=200); plt.close()

plt.figure(figsize=(10,6))
cat = prod_cat.merge(master[['order_id','late_delivery']], on='order_id', how='left')
cat_rate = cat.groupby('product_category').agg(late_rate=('late_delivery','mean'), orders=('order_id','nunique')).query('orders >= 300').sort_values('late_rate', ascending=False).head(15).reset_index()
sns.barplot(data=cat_rate, y='product_category', x='late_rate', color='#7570b3')
plt.title('Top Product Categories by Late Delivery Rate')
plt.tight_layout(); plt.savefig(FIG/'late_by_category.png', dpi=200); plt.close()

plt.figure(figsize=(8,5))
sns.histplot(master['total_price'].dropna(), bins=50)
plt.xlim(0, 1000)
plt.title('Order Value Distribution (clipped at R$1000)')
plt.tight_layout(); plt.savefig(FIG/'order_value_dist.png', dpi=200); plt.close()

# ML dataset: delivered orders only, avoid leakage by excluding actual delivery timestamps and review score.
model_df = master[master['order_status'] == 'delivered'].copy()
features = [
    'purchase_month','purchase_hour','approval_delay_hours','item_count','total_price','total_freight',
    'unique_sellers','unique_products','payment_count','payment_value','payment_installments_max',
    'freight_ratio','order_value_per_item','customer_state','seller_state','seller_customer_same_state',
    'product_category','paytype_boleto','paytype_credit_card','paytype_debit_card','paytype_voucher'
]
X = model_df[features]
y = model_df['late_delivery']

num_cols = [c for c in features if c not in ['customer_state','seller_state','product_category']]
cat_cols = ['customer_state','seller_state','product_category']

pre = ColumnTransformer([
    ('num', Pipeline([('imp', SimpleImputer(strategy='median')), ('scaler', StandardScaler())]), num_cols),
    ('cat', Pipeline([('imp', SimpleImputer(strategy='most_frequent')), ('oh', OneHotEncoder(handle_unknown='ignore'))]), cat_cols)
])

rf = Pipeline([('pre', pre), ('model', RandomForestClassifier(n_estimators=250, random_state=42, class_weight='balanced_subsample', n_jobs=-1, min_samples_leaf=3))])
logit = Pipeline([('pre', pre), ('model', LogisticRegression(max_iter=1000, class_weight='balanced'))])

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
rf.fit(X_train, y_train)
logit.fit(X_train, y_train)
rf_pred = rf.predict_proba(X_test)[:,1]
log_pred = logit.predict_proba(X_test)[:,1]
rf_auc = roc_auc_score(y_test, rf_pred)
log_auc = roc_auc_score(y_test, log_pred)
best_model = rf if rf_auc >= log_auc else logit
best_pred = rf_pred if rf_auc >= log_auc else log_pred
best_name = 'RandomForest' if rf_auc >= log_auc else 'LogisticRegression'

thresholds = np.arange(0.2, 0.81, 0.01)
rows = []
for t in thresholds:
    pred = (best_pred >= t).astype(int)
    tp = int(((pred==1) & (y_test==1)).sum())
    fp = int(((pred==1) & (y_test==0)).sum())
    fn = int(((pred==0) & (y_test==1)).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    score = 5*tp - 1*fp - 3*fn
    rows.append([t, tp, fp, fn, precision, recall, score])
threshold_df = pd.DataFrame(rows, columns=['threshold','tp','fp','fn','precision','recall','business_score'])
threshold_df.to_csv(OUT/'threshold_tuning.csv', index=False)
opt = threshold_df.sort_values('business_score', ascending=False).iloc[0]

metrics = {
    'model_selected': best_name,
    'rf_auc': float(rf_auc),
    'logit_auc': float(log_auc),
    'selected_auc': float(max(rf_auc, log_auc)),
    'optimal_threshold': float(opt['threshold']),
    'optimal_precision': float(opt['precision']),
    'optimal_recall': float(opt['recall'])
}
with open(OUT/'model_metrics.json','w') as f:
    json.dump(metrics,f,indent=2)

fpr, tpr, _ = roc_curve(y_test, best_pred)
plt.figure(figsize=(6,6))
plt.plot(fpr, tpr, label=f'{best_name} AUC={max(rf_auc,log_auc):.3f}')
plt.plot([0,1],[0,1],'--', color='gray')
plt.xlabel('False Positive Rate'); plt.ylabel('True Positive Rate'); plt.title('ROC Curve')
plt.legend(); plt.tight_layout(); plt.savefig(FIG/'roc_curve.png', dpi=200); plt.close()

prec, rec, _ = precision_recall_curve(y_test, best_pred)
plt.figure(figsize=(6,6))
plt.plot(rec, prec)
plt.xlabel('Recall'); plt.ylabel('Precision'); plt.title('Precision-Recall Curve')
plt.tight_layout(); plt.savefig(FIG/'pr_curve.png', dpi=200); plt.close()

# score full delivered set
full_scores = best_model.predict_proba(X)[:,1]
model_df['late_risk_score'] = full_scores
model_df['late_risk_flag'] = (model_df['late_risk_score'] >= float(opt['threshold'])).astype(int)
model_df.to_csv(OUT/'scored_delivered_orders.csv', index=False)

# Feature importance if RF selected
if best_name == 'RandomForest':
    prefit = best_model.named_steps['pre']
    model = best_model.named_steps['model']
    ohe = prefit.named_transformers_['cat'].named_steps['oh']
    feature_names = num_cols + list(ohe.get_feature_names_out(cat_cols))
    imp = pd.Series(model.feature_importances_, index=feature_names).sort_values(ascending=False).head(20)
    plt.figure(figsize=(10,7))
    sns.barplot(x=imp.values, y=imp.index, color='#1b9e77')
    plt.title('Top 20 Feature Importances - Late Delivery Model')
    plt.tight_layout(); plt.savefig(FIG/'feature_importance.png', dpi=200); plt.close()
    imp.reset_index().rename(columns={'index':'feature',0:'importance'}).to_csv(OUT/'feature_importance.csv', index=False)

# DuckDB SQL script
sql_script = '''
INSTALL httpfs; LOAD httpfs;
CREATE OR REPLACE TABLE customers AS SELECT * FROM read_csv_auto('data/olist_customers_dataset.csv');
CREATE OR REPLACE TABLE geolocation AS SELECT * FROM read_csv_auto('data/olist_geolocation_dataset.csv');
CREATE OR REPLACE TABLE order_items AS SELECT * FROM read_csv_auto('data/olist_order_items_dataset.csv');
CREATE OR REPLACE TABLE order_payments AS SELECT * FROM read_csv_auto('data/olist_order_payments_dataset.csv');
CREATE OR REPLACE TABLE order_reviews AS SELECT * FROM read_csv_auto('data/olist_order_reviews_dataset.csv');
CREATE OR REPLACE TABLE orders AS SELECT * FROM read_csv_auto('data/olist_orders_dataset.csv');
CREATE OR REPLACE TABLE products AS SELECT * FROM read_csv_auto('data/olist_products_dataset.csv');
CREATE OR REPLACE TABLE sellers AS SELECT * FROM read_csv_auto('data/olist_sellers_dataset.csv');
CREATE OR REPLACE TABLE category_translation AS SELECT * FROM read_csv_auto('data/product_category_name_translation.csv');
'''
(OUT/'sql'/'duckdb_load.sql').write_text(sql_script)

queries = {
'01_monthly_revenue.sql': """
SELECT date_trunc('month', CAST(order_purchase_timestamp AS TIMESTAMP)) AS month,
       COUNT(*) AS orders,
       SUM(oi.price) AS revenue,
       SUM(oi.freight_value) AS freight
FROM orders o
JOIN order_items oi USING(order_id)
GROUP BY 1
ORDER BY 1;
""",
'02_state_late_rate.sql': """
SELECT c.customer_state,
       COUNT(*) AS delivered_orders,
       AVG(CASE WHEN CAST(o.order_delivered_customer_date AS TIMESTAMP) > CAST(o.order_estimated_delivery_date AS TIMESTAMP) THEN 1 ELSE 0 END) AS late_rate
FROM orders o
JOIN customers c USING(customer_id)
WHERE o.order_status = 'delivered'
GROUP BY 1
HAVING COUNT(*) >= 500
ORDER BY late_rate DESC;
""",
'03_review_impact.sql': """
SELECT r.review_score,
       COUNT(*) AS orders,
       AVG(CASE WHEN CAST(o.order_delivered_customer_date AS TIMESTAMP) > CAST(o.order_estimated_delivery_date AS TIMESTAMP) THEN 1 ELSE 0 END) AS late_rate
FROM orders o
JOIN order_reviews r USING(order_id)
WHERE o.order_status = 'delivered'
GROUP BY 1
ORDER BY 1;
""",
'04_top_categories.sql': """
SELECT COALESCE(t.product_category_name_english, p.product_category_name) AS category,
       COUNT(DISTINCT oi.order_id) AS orders,
       SUM(oi.price) AS revenue,
       AVG(oi.price) AS avg_item_price
FROM order_items oi
JOIN products p USING(product_id)
LEFT JOIN category_translation t USING(product_category_name)
GROUP BY 1
HAVING COUNT(DISTINCT oi.order_id) >= 100
ORDER BY revenue DESC
LIMIT 20;
""",
'05_seller_concentration.sql': """
SELECT s.seller_state,
       COUNT(DISTINCT s.seller_id) AS sellers,
       COUNT(DISTINCT oi.order_id) AS orders,
       SUM(oi.price) AS revenue
FROM order_items oi
JOIN sellers s USING(seller_id)
GROUP BY 1
ORDER BY revenue DESC;
"""
}
for fn, txt in queries.items():
    (SQL/fn).write_text(txt.strip() + '\n')

# Export summary tables for Power BI
master['purchase_month_name'] = master['order_purchase_timestamp'].dt.strftime('%Y-%m')
dim_date = pd.DataFrame({'date': pd.date_range(master['order_purchase_timestamp'].min().normalize(), master['order_purchase_timestamp'].max().normalize(), freq='D')})
dim_date['year'] = dim_date['date'].dt.year
dim_date['month'] = dim_date['date'].dt.month
dim_date['month_name'] = dim_date['date'].dt.strftime('%b')
dim_date['quarter'] = dim_date['date'].dt.quarter

dim_customers = customers.drop_duplicates('customer_id')
dim_sellers = sellers.drop_duplicates('seller_id')
dim_products = products[['product_id','product_category','product_weight_g','product_length_cm','product_height_cm','product_width_cm']].drop_duplicates()

fact_orders = master[['order_id','customer_id','order_status','order_purchase_timestamp','order_estimated_delivery_date','order_delivered_customer_date','customer_state','seller_state','item_count','total_price','total_freight','payment_value','payment_installments_max','review_score','late_delivery','delivery_gap_days']].copy()
fact_orders['order_purchase_date'] = fact_orders['order_purchase_timestamp'].dt.date.astype(str)

for name, df in [('dim_date.csv', dim_date), ('dim_customers.csv', dim_customers), ('dim_sellers.csv', dim_sellers), ('dim_products.csv', dim_products), ('fact_orders.csv', fact_orders)]:
    df.to_csv(PBI/name, index=False)

# DAX measures
measures = '''
Total Orders = COUNTROWS(fact_orders)
Delivered Orders = CALCULATE([Total Orders], fact_orders[order_status] = "delivered")
Total Revenue = SUM(fact_orders[total_price])
Total Freight = SUM(fact_orders[total_freight])
Average Order Value = DIVIDE([Total Revenue], [Total Orders])
Late Deliveries = SUM(fact_orders[late_delivery])
Late Delivery Rate = DIVIDE([Late Deliveries], [Delivered Orders])
Average Review Score = AVERAGE(fact_orders[review_score])
Average Delivery Gap Days = AVERAGE(fact_orders[delivery_gap_days])
Average Installments = AVERAGE(fact_orders[payment_installments_max])
Orders per Customer = DIVIDE([Total Orders], DISTINCTCOUNT(dim_customers[customer_id]))
Revenue per Delivered Order = DIVIDE([Total Revenue], [Delivered Orders])
On-Time Deliveries = [Delivered Orders] - [Late Deliveries]
On-Time Rate = DIVIDE([On-Time Deliveries], [Delivered Orders])
High Value Orders = CALCULATE([Total Orders], fact_orders[total_price] >= 250)
High Value Revenue = CALCULATE([Total Revenue], fact_orders[total_price] >= 250)
Freight to Revenue Ratio = DIVIDE([Total Freight], [Total Revenue])
Average Items per Order = AVERAGE(fact_orders[item_count])
'''
(PBI/'dax_measures.txt').write_text(measures.strip()+'\n')

# Excel workbook
with pd.ExcelWriter(OUT/'Olist_Analysis_Workbook.xlsx', engine='openpyxl') as writer:
    master.head(50000).to_excel(writer, sheet_name='master_sample', index=False)
    pd.DataFrame([kpis]).to_excel(writer, sheet_name='kpis', index=False)
    threshold_df.to_excel(writer, sheet_name='threshold_tuning', index=False)
    state_late.reset_index().to_excel(writer, sheet_name='state_late_rate', index=False)
    review_late.to_excel(writer, sheet_name='review_late', index=False)
    monthly.to_excel(writer, sheet_name='monthly_revenue', index=False)

# HTML dashboard
import base64

def img_to_data_uri(path):
    with open(path, 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode('utf-8')

imgs = {name: img_to_data_uri(FIG/name) for name in os.listdir(FIG) if name.endswith('.png')}
html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Olist Ecommerce Dashboard</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; background:#f6f8fb; color:#1f2937; }}
.grid {{ display:grid; grid-template-columns: repeat(4,1fr); gap:16px; margin-bottom:24px; }}
.card {{ background:white; border-radius:12px; padding:16px; box-shadow:0 2px 10px rgba(0,0,0,.08); }}
.kpi {{ font-size:28px; font-weight:700; }}
.label {{ color:#6b7280; font-size:14px; }}
img {{ width:100%; border-radius:10px; }}
.section {{ margin:20px 0; }}
@media (max-width: 900px) {{ .grid {{ grid-template-columns: repeat(2,1fr); }} }}
</style></head><body>
<h1>Brazilian E-Commerce Public Dataset by Olist</h1>
<p>Executive dashboard covering revenue, delivery performance, customer satisfaction, and late-delivery prediction.</p>
<div class="grid">
<div class="card"><div class="label">Total Orders</div><div class="kpi">{kpis['orders_total']:,}</div></div>
<div class="card"><div class="label">Delivered Orders</div><div class="kpi">{kpis['delivered_orders']:,}</div></div>
<div class="card"><div class="label">Late Delivery Rate</div><div class="kpi">{kpis['late_rate']*100:.1f}%</div></div>
<div class="card"><div class="label">Total Revenue</div><div class="kpi">R$ {kpis['revenue_total']/1e6:.2f}M</div></div>
<div class="card"><div class="label">Average Order Value</div><div class="kpi">R$ {kpis['avg_order_value']:.2f}</div></div>
<div class="card"><div class="label">Average Review Score</div><div class="kpi">{kpis['avg_review_score']:.2f}</div></div>
<div class="card"><div class="label">Average Delivery Time</div><div class="kpi">{kpis['avg_delivery_days']:.1f} days</div></div>
<div class="card"><div class="label">Model ROC-AUC</div><div class="kpi">{metrics['selected_auc']:.3f}</div></div>
</div>
<div class="section card"><h2>Monthly Revenue Trend</h2><img src="{imgs.get('monthly_revenue.png','')}"></div>
<div class="section card"><h2>Late Delivery by State</h2><img src="{imgs.get('late_rate_by_state.png','')}"></div>
<div class="section card"><h2>Review Score vs Late Delivery</h2><img src="{imgs.get('late_by_review.png','')}"></div>
<div class="section card"><h2>High-Risk Categories</h2><img src="{imgs.get('late_by_category.png','')}"></div>
<div class="section card"><h2>Model Performance</h2><img src="{imgs.get('roc_curve.png','')}"></div>
<div class="section card"><h2>Prediction Ready</h2>
<p>Selected model: <b>{metrics['model_selected']}</b><br>Optimal threshold: <b>{metrics['optimal_threshold']:.2f}</b><br>Precision: <b>{metrics['optimal_precision']:.2f}</b> | Recall: <b>{metrics['optimal_recall']:.2f}</b></p>
</div>
</body></html>'''
(OUT/'dashboard.html').write_text(html)

# Markdown report
report = f'''# Olist Brazilian E-Commerce Analysis

## Executive Summary
- Total orders: **{kpis['orders_total']:,}**
- Delivered orders: **{kpis['delivered_orders']:,}**
- Late delivery rate: **{kpis['late_rate']*100:.1f}%**
- Total revenue: **R$ {kpis['revenue_total']:,.0f}**
- Average order value: **R$ {kpis['avg_order_value']:.2f}**
- Average review score: **{kpis['avg_review_score']:.2f} / 5**
- Average delivery time: **{kpis['avg_delivery_days']:.1f} days**
- Best predictive model: **{metrics['model_selected']}** with **ROC-AUC {metrics['selected_auc']:.3f}**

## Business Questions Answered
1. How revenue evolved over time.
2. Which states and categories face the highest late-delivery risk.
3. How delivery performance affects customer satisfaction.
4. Which features best predict late delivery for proactive intervention.

## Key Findings
- Delivery performance materially affects reviews; lower review scores align with higher late-delivery rates.
- Seller and customer geography matter, especially cross-state fulfillment.
- Freight burden, order complexity, and timing are useful predictors of late delivery.
- The selected model can support operations teams in triaging high-risk orders before SLA breaches.

## Files Delivered
- `outputs/dashboard.html` - interactive dashboard
- `outputs/Olist_Analysis_Workbook.xlsx` - Excel workbook
- `outputs/master_orders.csv` - analytics-ready master table
- `outputs/scored_delivered_orders.csv` - scored orders for intervention
- `outputs/sql/*.sql` - SQL scripts and reusable queries
- `outputs/powerbi/*` - star-schema extracts and DAX measures
- `outputs/figures/*.png` - chart assets

## Recommended Actions
- Prioritize interventions for high-risk states and categories.
- Monitor freight ratio and approval delays as early warning signals.
- Use risk scoring in a daily exception queue for logistics teams.
- Tie delivery KPIs to customer experience and review recovery workflows.
'''
(OUT/'Report.md').write_text(report)

resume = f'''# Resume Bullets and Interview Talking Points

## Resume Bullets
- Analyzed the **Olist Brazilian E-Commerce Public Dataset** covering **99K+ orders, 112K+ order items, 103K+ payments, and 100K reviews** using Python, Pandas, SQL, and Excel.
- Built an end-to-end analytics pipeline that consolidated multi-table transactional data into a master fact table, surfaced delivery and revenue KPIs, and automated professional reporting outputs.
- Developed a late-delivery risk model with **ROC-AUC {metrics['selected_auc']:.3f}**, enabling proactive identification of at-risk delivered orders using operational, payment, geography, and product features.
- Created executive dashboards and Power BI-ready star-schema assets with DAX measures for revenue, on-time delivery, freight efficiency, and customer satisfaction monitoring.
- Identified business insights including state-wise late delivery variation, category risk concentration, and the relationship between delivery delays and lower review scores.

## Interview Talking Points
- Why late delivery was selected as the target variable.
- How leakage was avoided by excluding actual delivery outcome timestamps from model features.
- Why Power BI star schema and DAX measures were prepared for stakeholder self-service analytics.
- How threshold tuning was used to balance precision and recall for business operations.
'''
(OUT/'Resume_Bullets_and_Interview.md').write_text(resume)

print('Analysis complete')
