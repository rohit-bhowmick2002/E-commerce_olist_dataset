# 🛒 E-Commerce Sales Analytics — Olist Brazilian Marketplace

> **End-to-end e-commerce analytics platform** — analyzing 99,441 orders, $16M+ in revenue, 96K customers, and 3,095 sellers across Brazil's largest online marketplace to uncover growth opportunities, operational bottlenecks, and customer behavior patterns.

---

## 📌 Project Overview

This project delivers a **comprehensive e-commerce intelligence system** built on the real-world Olist dataset — one of the most complete public e-commerce datasets available. It covers the full analytical lifecycle from SQL data modeling and multi-table joins to an interactive HTML dashboard, answering 24 structured business questions across 12 analytical levels.

**Domain:** E-Commerce · Retail Analytics · Customer Intelligence  
**Stack:** SQL (PostgreSQL) · Python · HTML/CSS/JS · Data Visualization  
**Data Scope:** Sep 2016 – Oct 2018 · 99K+ orders · 96K customers · 3,095 sellers · 73 product categories

---

## 📊 Key Business Impact

| Metric | Value |
|--------|-------|
| 💰 Total Revenue Analyzed | **$16,008,872** |
| 🛒 Total Orders | **99,441** |
| 👥 Unique Customers | **96,096** |
| 🏪 Active Sellers | **3,095** across 23 states |
| 📦 Total Order Items | **112,650** |
| 🏷️ Product Catalogue | **32,951 products** across 73 categories |
| ⭐ Average Customer Rating | **4.09 / 5.00** |
| 🚚 Average Delivery Time | **12.1 days** |
| ⏰ Late Delivery Rate | **8.1%** (7,827 orders) |
| 💳 Average Order Value | **$160.99** |
| ❌ Cancellation Rate | **0.63%** — exceptionally low |
| 🔁 Customer Retention Rate | **3.12%** — signals high acquisition dependency |

---

## 🗂️ Data Architecture

Star-schema relational model with **4 dimension tables** and **5 fact/transactional tables**:

```
customers                        → 99,441 records, mapped to unique_id, city & state
sellers                          → 3,095 sellers across 23 Brazilian states
products                         → 32,951 products across 73 categories
product_category_name_translation → Portuguese → English category mapping

orders          → Full order lifecycle: purchase → approval → delivery
order_items     → 112,650 line items with price & freight breakdown
payments        → Multi-type payment tracking (credit card, boleto, voucher, debit)
reviews         → 99,224 customer reviews with scores & comment text
geolocation     → Lat/lng coordinates mapped to zip codes for spatial analysis
```

---

## 🔍 Analytical Framework — 12 Levels, 24 Business Questions

### 🟢 Level 1–2 · Business Fundamentals & Customer Analysis
- Total orders, revenue, and monthly revenue trend
- Top customers by lifetime spend
- Customer retention rate (**3.12%** — highlights churn risk)

### 🟡 Level 3–4 · Operations & Satisfaction
- Average delivery time: **12.1 days** end-to-end
- Late delivery identification: **7,827 orders (8.1%)** missed estimated date
- Delivery time vs. review score correlation — operational impact on customer satisfaction

### 🟠 Level 5–6 · Revenue & Geography
- Top revenue categories: **Health & Beauty ($1.26M) · Watches & Gifts ($1.21M) · Bed & Bath ($1.04M)**
- Average Order Value: **$160.99**
- Top cities: São Paulo (15,540 orders), Rio de Janeiro (6,882), Belo Horizonte (2,773)
- Revenue concentration: **SP state drives the majority of national revenue**

### 🔵 Level 7–8 · Seller Performance & Problem Detection
- Top sellers by revenue with delivery speed benchmarking
- High freight cost order identification
- Cancellation rate analysis: **0.63%** — strong fulfilment health

### 🟣 Level 9–10 · Time Intelligence & Window Functions
- Peak order hour analysis for demand forecasting
- Weekend vs. weekday revenue segmentation
- Running cumulative revenue with SQL window functions (`SUM OVER`)
- Top product per category using `RANK() OVER PARTITION BY`

### 🔴 Level 11–12 · Advanced & Expert Analytics
- Low-rated product flagging (avg score < 3) for catalogue optimization
- Repeat customer identification and purchase frequency distribution
- **RFM Analysis** — Recency, Frequency, Monetary segmentation
- **Customer Lifetime Value (CLTV)** — ranked across entire customer base

---

## 💳 Payment Intelligence

| Payment Type | Orders |
|---|---|
| Credit Card | 76,795 (74.2%) |
| Boleto (Bank Slip) | 19,784 (19.1%) |
| Voucher | 5,775 (5.6%) |
| Debit Card | 1,529 (1.5%) |

> Credit card dominance signals strong instalment payment behaviour — confirmed by `payment_installments` analysis.

---

## 🛠️ Technical Implementation

```sql
-- PostgreSQL star-schema with 9 normalized tables
-- Multi-level JOINs across orders → customers → payments → reviews → products
-- Window functions: RANK(), SUM() OVER, DATE_TRUNC, EXTRACT
-- Analytical patterns: RFM, CLTV, retention cohorts, running totals
-- Subqueries, CTEs, FILTER aggregation, HAVING clauses
```

**SQL Complexity Levels covered:**
- ✅ Basic aggregation & GROUP BY
- ✅ Multi-table JOINs (up to 4 tables)
- ✅ Subqueries & derived tables
- ✅ Window functions (RANK, SUM OVER)
- ✅ Conditional aggregation (FILTER WHERE)
- ✅ RFM & CLTV business logic

---

## 📁 Repository Structure

```
├── E-commerce_Sales_olist_dataset.sql        # Full schema DDL + 24 analytical queries
├── olist_dashboard.html                      # Interactive analytics dashboard
├── olist_orders_dataset.csv                  # 99,441 order records
├── olist_customers_dataset.csv               # 99,441 customer records
├── olist_order_items_dataset.csv             # 112,650 line items
├── olist_order_payments_dataset.csv          # Payment records
├── olist_order_reviews_dataset.csv           # 99,224 customer reviews
├── olist_products_dataset.csv                # 32,951 products
├── olist_sellers_dataset.csv                 # 3,095 seller records
├── olist_geolocation_dataset.csv             # Lat/lng geospatial data
└── product_category_name_translation.csv     # PT → EN category mapping
```

---

## 🚀 Getting Started

**Set up the database:**
```sql
-- Run E-commerce_Sales_olist_dataset.sql in PostgreSQL
-- Tables auto-created in correct FK dependency order
-- Import CSVs using COPY or pgAdmin import wizard
```

**View the dashboard:**
```bash
open olist_dashboard.html   # No server required
```

**Quick data exploration:**
```python
import pandas as pd
orders = pd.read_csv("olist_orders_dataset.csv")
payments = pd.read_csv("olist_order_payments_dataset.csv")
print(payments['payment_value'].sum())   # → $16,008,872
```

---

## 💡 Key Business Insights Uncovered

- 📍 **Geographic concentration risk** — São Paulo alone accounts for ~42% of all orders
- 🔁 **Retention gap** — only 3.12% of customers reorder, indicating heavy reliance on new customer acquisition
- ⭐ **Delivery drives ratings** — orders delivered on time consistently score 4–5 stars; late orders cluster at 1–2 stars
- 🏷️ **Health & Beauty** is the single highest-revenue category at $1.26M
- 💳 **74% of payments** are by credit card — instalment flexibility is a key purchase driver
- 🚚 **8.1% late delivery rate** — a primary lever for improving customer satisfaction scores

---

## 👤 Author

**Rohit Bhowmick** — Data Analyst  
*SQL · Python · Tableau · Power BI*

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat&logo=linkedin)](https://linkedin.com/in/rohit-bhowmick)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?style=flat&logo=github)](https://github.com/rohit-bhowmick2002)

---

*Built to demonstrate real-world e-commerce analytics competency: relational data modelling, multi-level SQL engineering, customer segmentation, operational diagnostics, and business storytelling through data.*
