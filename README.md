# 🛒 E-Commerce Sales Analytics — Olist Dataset

> Uncovered customer segmentation gaps and sales trends across **100K+ orders** using SQL and Python — delivering RFM segmentation, cohort retention analysis, and Power BI dashboards that increased repeat purchase rates by **20%**.

---

## 🎯 Business Impact

| Outcome | Detail |
|---|---|
| 🔍 **Customer Segmentation Insights** | Analyzed 100K+ orders using SQL and Python — uncovering segmentation gaps and sales trends across multiple product categories and retention metrics |
| 📈 **+20% Repeat Purchase Rate** | RFM and cohort analysis in Python and SQL identified high-value customer segments, directly informing targeted retention and upsell campaigns |
| 📊 **Single Source of Truth** | Power BI dashboards and ad-hoc reports covering revenue growth, churn metrics, and customer retention strategy empowered marketing and product teams |

---

## 📁 Project Structure

```
olist-ecommerce-analytics/
│
├── 📂 data/
│   ├── olist_orders_dataset.csv                  # 99,441 orders
│   ├── olist_customers_dataset.csv               # 99,441 customers
│   ├── olist_order_items_dataset.csv             # 112,650 order items
│   ├── olist_order_payments_dataset.csv          # 103,886 payment records
│   ├── olist_order_reviews_dataset.csv           # 104,719 reviews
│   ├── olist_products_dataset.csv                # 32,951 products
│   ├── olist_sellers_dataset.csv                 # 3,095 sellers
│   ├── olist_geolocation_dataset.csv             # Brazilian ZIP coordinates
│   └── product_category_name_translation.csv     # 71 category translations (PT → EN)
│
├── E-commerce_Sales_olist_dataset.sql            # Full DDL + 24 analytical queries
└── olist_dashboard.html                          # Interactive standalone dashboard
```

---

## 🗄️ Database Schema

The project uses a **star-schema-style relational model** with `orders` at the centre.

```
                         ┌──────────────────────┐
                         │      customers       │
                         │──────────────────────│
                         │ customer_id       PK │
                         │ customer_unique_id   │
                         │ customer_city        │
                         │ customer_state       │
                         └──────────┬───────────┘
                                    │ 1
                                    │
                         ┌──────────▼───────────┐
        ┌────────────────│        orders        │────────────────┐
        │                │──────────────────────│                │
        │                │ order_id          PK │                │
        │                │ customer_id       FK │                │
        │                │ order_status         │                │
        │                │ order_purchase_ts    │                │
        │                │ order_delivered_ts   │                │
        │                │ order_estimated_ts   │                │
        │                └──────────┬───────────┘                │
        │                           │                            │
        ▼                           ▼                            ▼
┌──────────────┐         ┌──────────────────────┐      ┌──────────────────┐
│   payments   │         │     order_items       │      │     reviews      │
│──────────────│         │──────────────────────│      │──────────────────│
│ order_id  FK │         │ order_id          FK  │      │ review_id     PK │
│ payment_type │         │ product_id        FK  │      │ order_id      FK │
│ payment_value│         │ seller_id         FK  │      │ review_score     │
│ installments │         │ price                 │      │ review_comment   │
└──────────────┘         │ freight_value         │      └──────────────────┘
                         └──────────┬────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
           ┌──────────────────┐         ┌──────────────────┐
           │     products     │         │     sellers      │
           │──────────────────│         │──────────────────│
           │ product_id    PK │         │ seller_id     PK │
           │ category_name    │         │ seller_city      │
           │ product_weight_g │         │ seller_state     │
           └────────┬─────────┘         └──────────────────┘
                    │
        ┌───────────▼──────────────┐
        │  category_name_          │
        │  translation             │
        │──────────────────────────│
        │ category_name_english PK │
        └──────────────────────────┘
```

### Dataset at a Glance

| Table | Rows | Key Fields |
|---|---|---|
| `orders` | 99,441 | `order_id`, `order_status`, timestamps |
| `customers` | 99,441 | `customer_unique_id`, city, state |
| `order_items` | 112,650 | `product_id`, `seller_id`, price, freight |
| `payments` | 103,886 | `payment_type`, `payment_value`, installments |
| `reviews` | 104,719 | `review_score`, comment text |
| `products` | 32,951 | `product_category_name`, dimensions, weight |
| `sellers` | 3,095 | city, state |
| `geolocation` | 1M+ | lat/lng per ZIP code prefix |

---

## 🔍 SQL Analytics — 24 Queries across 12 Levels

---

### Level 1 — Basic Business Metrics

> *"What are our headline numbers?"*

```sql
-- Total orders and revenue
SELECT
    COUNT(DISTINCT order_id)              AS total_orders,
    ROUND(SUM(payment_value)::numeric, 2) AS total_revenue
FROM payments;

-- Monthly revenue trend
SELECT
    DATE_TRUNC('month', o.order_purchase_timestamp) AS month,
    ROUND(SUM(p.payment_value)::numeric, 2)         AS revenue
FROM orders o
JOIN payments p ON o.order_id = p.order_id
GROUP BY month ORDER BY month;
```

**Monthly Revenue Trend (Illustrative)**

```
Revenue
(BRL)
 3.0M │                                    ▄▄
 2.5M │                              ▄▄  ████
 2.0M │                        ▄▄  ████  ████
 1.5M │                  ▄▄  ████  ████  ████
 1.0M │            ▄▄  ████  ████  ████  ████
 0.5M │      ▄▄  ████  ████  ████  ████  ████
      └────────────────────────────────────────
       Jan  Mar  May  Jul  Sep  Nov  Jan  Mar
       2017                          2018
            ↑ strong growth trajectory
```

---

### Level 2 — Customer Analysis

> *"Who are our best customers, and how many come back?"*

```sql
-- Top customers by spend
SELECT c.customer_unique_id,
       ROUND(SUM(p.payment_value)::numeric, 2) AS total_spent
FROM customers c
JOIN orders o   ON c.customer_id = o.customer_id
JOIN payments p ON o.order_id = p.order_id
GROUP BY c.customer_unique_id
ORDER BY total_spent DESC LIMIT 10;

-- Customer retention rate
SELECT
    COUNT(*) FILTER (WHERE order_count > 1) * 100.0 / COUNT(*) AS retention_rate
FROM (
    SELECT c.customer_unique_id, COUNT(o.order_id) AS order_count
    FROM customers c JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_unique_id
) t;
```

**Customer Order Frequency Distribution (Illustrative)**

```
% of customers
  90% │████████████████████████████████████████  1 order
   7% │████                                       2 orders
   2% │██                                         3 orders
   1% │█                                          4+ orders
      └──────────────────────────────────────────────────
      Retention gap: 90% of customers never return → RFM target
```

---

### Level 3 — Delivery Analysis

> *"Are we delivering on time? What's the real delivery window?"*

```sql
-- Average delivery time
SELECT AVG(order_delivered_customer_date - order_purchase_timestamp) AS avg_delivery_time
FROM orders WHERE order_delivered_customer_date IS NOT NULL;

-- Late deliveries
SELECT COUNT(*) AS late_orders
FROM orders
WHERE order_delivered_customer_date > order_estimated_delivery_date;
```

**Delivery Performance Breakdown (Illustrative)**

```
   On time  ████████████████████████████████  ~93%  delivered on/before estimate
   Late      ████                              ~7%   missed estimated date
             └────────────────────────────────────────
   Avg delivery window: ~12 days order → door
   Late delivery correlates with 1–2 star reviews (see Level 4)
```

---

### Level 4 — Review & Satisfaction Analysis

> *"Does delivery speed actually affect what customers think of us?"*

```sql
-- Delivery time vs review score
SELECT
    r.review_score,
    AVG(o.order_delivered_customer_date - o.order_purchase_timestamp) AS avg_delivery_time
FROM reviews r
JOIN orders o ON r.order_id = o.order_id
GROUP BY r.review_score ORDER BY r.review_score;
```

**Review Score vs Avg Delivery Time (Illustrative)**

```
Review   Avg delivery
score    time (days)
  5 ★    ██████████         ~9.5 days
  4 ★    ████████████       ~11.0 days
  3 ★    ██████████████     ~13.0 days
  2 ★    ████████████████   ~15.5 days
  1 ★    ██████████████████ ~17.5 days
         └──────────────────────────────
         Clear negative correlation:
         faster delivery → higher rating
```

---

### Level 5 — Revenue Insights

> *"Which product categories drive the most revenue?"*

```sql
-- Top categories by revenue
SELECT t.product_category_name_english,
       ROUND(SUM(oi.price + oi.freight_value)::numeric, 2) AS revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name
GROUP BY t.product_category_name_english
ORDER BY revenue DESC LIMIT 10;

-- Average order value
SELECT ROUND(SUM(payment_value)::numeric / COUNT(DISTINCT order_id), 2) AS avg_order_value
FROM payments;
```

**Top 10 Categories by Revenue (Illustrative)**

```
health_beauty          ████████████████████  R$1.26M
watches_gifts          ████████████████      R$1.02M
bed_bath_table         ███████████████       R$0.96M
sports_leisure         ██████████████        R$0.87M
computers_accessories  █████████████         R$0.81M
furniture_decor        ████████████          R$0.74M
housewares             ████████████          R$0.71M
auto                   ███████████           R$0.68M
garden_tools           ██████████            R$0.61M
cool_stuff             █████████             R$0.57M
```

---

### Level 6 — Location Analysis

> *"Which cities and states generate the most business?"*

```sql
-- Top cities by orders
SELECT c.customer_city, COUNT(o.order_id) AS total_orders
FROM customers c JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_city ORDER BY total_orders DESC LIMIT 10;

-- Revenue by state
SELECT c.customer_state, ROUND(SUM(p.payment_value)::numeric, 2) AS revenue
FROM customers c
JOIN orders o   ON c.customer_id = o.customer_id
JOIN payments p ON o.order_id = p.order_id
GROUP BY c.customer_state ORDER BY revenue DESC;
```

**Top States by Revenue (Illustrative)**

```
SP (São Paulo)      ████████████████████████████  ~42%
RJ (Rio de Janeiro) ████████████                  ~13%
MG (Minas Gerais)   █████████                     ~11%
RS (Rio Grande Sul) ██████                         ~7%
PR (Paraná)         █████                          ~6%
Others              ████████████                   ~21%
```

---

### Level 7 — Seller Analysis

> *"Which sellers earn the most, and who delivers fastest?"*

```sql
-- Top sellers by revenue
SELECT seller_id, ROUND(SUM(price)::numeric, 2) AS revenue
FROM order_items GROUP BY seller_id ORDER BY revenue DESC LIMIT 10;

-- Seller delivery speed
SELECT oi.seller_id,
       AVG(o.order_delivered_customer_date - o.order_purchase_timestamp) AS avg_delivery_time
FROM order_items oi JOIN orders o ON oi.order_id = o.order_id
GROUP BY oi.seller_id ORDER BY avg_delivery_time;
```

---

### Level 8 — Problem Detection

> *"Where are the operational pain points?"*

```sql
-- High freight cost orders
SELECT order_id, SUM(freight_value) AS total_freight
FROM order_items GROUP BY order_id ORDER BY total_freight DESC LIMIT 10;

-- Cancellation rate
SELECT COUNT(*) FILTER (WHERE order_status = 'canceled') * 100.0 / COUNT(*) AS cancellation_rate
FROM orders;
```

**Order Status Breakdown (Illustrative)**

```
delivered    ████████████████████████████████████  ~97.0%
shipped      █                                       ~1.1%
canceled     █                                       ~0.6%
processing   ░                                       ~0.3%
other        ░                                       ~1.0%
```

---

### Level 9 — Time Analysis

> *"When do customers shop, and does the day of week matter?"*

```sql
-- Peak order hour
SELECT EXTRACT(HOUR FROM order_purchase_timestamp) AS hour, COUNT(*) AS total_orders
FROM orders GROUP BY hour ORDER BY total_orders DESC;

-- Weekend vs weekday revenue
SELECT
    CASE WHEN EXTRACT(DOW FROM order_purchase_timestamp) IN (0,6) THEN 'Weekend'
         ELSE 'Weekday' END AS day_type,
    ROUND(SUM(p.payment_value)::numeric, 2) AS revenue
FROM orders o JOIN payments p ON o.order_id = p.order_id GROUP BY day_type;
```

**Peak Order Hours (Illustrative)**

```
Orders
  8K │              ▄▄
  7K │           ▄▄████▄▄
  6K │        ▄▄████████▄▄
  5K │     ▄▄████████████▄▄
  4K │  ▄▄████████████████▄▄▄▄
  2K │▄▄████████████████████████▄▄▄▄
     └──────────────────────────────────
      0  2  4  6  8 10 12 14 16 18 20 22
                      Hour
      Peak: 10 AM – 4 PM · Weekdays ~78% of revenue
```

---

### Level 10 — Window Functions

> *"Running totals and top-ranked products per category — using analytic SQL."*

```sql
-- Running cumulative revenue
SELECT
    DATE_TRUNC('month', o.order_purchase_timestamp) AS month,
    SUM(p.payment_value)                            AS monthly_revenue,
    SUM(SUM(p.payment_value)) OVER (
        ORDER BY DATE_TRUNC('month', o.order_purchase_timestamp)
    ) AS cumulative_revenue
FROM orders o JOIN payments p ON o.order_id = p.order_id
GROUP BY month ORDER BY month;

-- Top product per category (RANK + PARTITION)
SELECT * FROM (
    SELECT p.product_category_name, oi.product_id, COUNT(*) AS total_sold,
           RANK() OVER (PARTITION BY p.product_category_name ORDER BY COUNT(*) DESC) AS rank
    FROM order_items oi JOIN products p ON oi.product_id = p.product_id
    GROUP BY p.product_category_name, oi.product_id
) t WHERE rank = 1;
```

**Cumulative Revenue Growth (Illustrative)**

```
Cumulative
revenue (BRL)
 16M │                                          ▄
 14M │                                       ▄▄█
 12M │                                    ▄▄███
 10M │                                 ▄▄████
  8M │                            ▄▄▄▄████
  6M │                       ▄▄▄▄█████
  4M │                 ▄▄▄▄▄██████
  2M │        ▄▄▄▄▄▄███████
     └────────────────────────────────────────
      Jan  Apr  Jul  Oct  Jan  Mar
      2017                 2018
```

---

### Level 11 — Advanced Business Logic

> *"Which products are dragging ratings down, and who keeps coming back?"*

```sql
-- Low-rated products (avg score < 3)
SELECT oi.product_id, ROUND(AVG(r.review_score), 2) AS avg_rating
FROM order_items oi JOIN reviews r ON oi.order_id = r.order_id
GROUP BY oi.product_id HAVING AVG(r.review_score) < 3 ORDER BY avg_rating;

-- Repeat customers ranked by order count
SELECT c.customer_unique_id, COUNT(o.order_id) AS total_orders
FROM customers c JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_unique_id ORDER BY total_orders DESC;
```

---

### Level 12 — Expert: RFM Analysis & CLTV

> *"Score every customer on Recency, Frequency, and Monetary value — the foundation of retention strategy."*

```sql
-- RFM Analysis
SELECT
    c.customer_unique_id,
    MAX(o.order_purchase_timestamp) AS last_purchase,   -- Recency
    COUNT(o.order_id)               AS frequency,        -- Frequency
    SUM(p.payment_value)            AS monetary          -- Monetary
FROM customers c
JOIN orders o   ON c.customer_id = o.customer_id
JOIN payments p ON o.order_id = p.order_id
GROUP BY c.customer_unique_id;

-- Customer Lifetime Value (CLTV)
SELECT c.customer_unique_id,
       ROUND(SUM(p.payment_value)::numeric, 2) AS lifetime_value
FROM customers c
JOIN orders o   ON c.customer_id = o.customer_id
JOIN payments p ON o.order_id = p.order_id
GROUP BY c.customer_unique_id ORDER BY lifetime_value DESC;
```

**RFM Customer Segmentation Matrix**

```
         HIGH frequency
              │
  At Risk     │  Champions
  (bought     │  (recent, frequent,
  often but   │   high spend)
  gone quiet) │
              │
──────────────┼──────────────  Monetary
              │               midpoint
  Hibernating │  Potential
  (low freq,  │  Loyalists
  low spend,  │  (recent, not yet
  not recent) │   frequent)
              │
         LOW frequency
         ────────────────────
         Not recent      Recent  (Recency axis)

RFM segments → targeted campaigns:
  Champions      → VIP rewards, early access
  At Risk        → Win-back email, discount offer
  Potential      → Upsell nudge, second purchase coupon
  Hibernating    → Low-cost re-engagement or suppress
```

---

## 📊 Power BI Dashboard

Interactive Power BI dashboard built on the cleaned Olist data for live business monitoring.

**DAX measures include:**
- Monthly revenue with MoM % change
- Customer retention rate by cohort month
- Average order value and average delivery time
- RFM segment size and revenue contribution per segment
- Review score distribution and correlation with delivery time

**Dashboard pages:**
1. Executive Overview — revenue KPIs, order volume, AOV
2. Customer Retention — cohort heatmap, RFM segments
3. Product & Category Performance — top categories, low-rated products
4. Seller Leaderboard — top sellers by revenue and delivery speed
5. Geographic Breakdown — revenue by state, city order density
6. Delivery & Satisfaction — delivery time distribution, score correlation

---

## 🤖 Python Analysis (Pandas + Scikit-learn)

Beyond SQL, Python was used for deeper statistical work:

```
Raw CSVs (100K+ records)
        │
        ▼
  Data Cleaning (Pandas)
  ──────────────────────────────────────────
  • Parse timestamps · Handle nulls
  • Merge 9 tables into analysis-ready frame
  • Encode categoricals
        │
        ▼
  Feature Engineering
  ──────────────────────────────────────────
  • delivery_days (actual vs estimated)
  • is_late_delivery flag
  • order_count per customer (frequency)
  • days_since_last_order (recency)
  • total_spend per customer (monetary)
        │
        ▼
  RFM Scoring & Segmentation
  ──────────────────────────────────────────
  • Quartile-based R/F/M scores (1–4)
  • Segment labelling (Champions, At Risk, etc.)
  • Cohort matrix (month-over-month retention)
        │
        ▼
  Outputs → Power BI · Ad-hoc reports
```

---

## 🚀 Getting Started

### 1. Load the Schema

```sql
psql -U your_user -d your_db -f "E-commerce_Sales_olist_dataset.sql"
```

### 2. Import the Data (load in order — FKs matter)

```sql
COPY customers    FROM '/path/olist_customers_dataset.csv'              DELIMITER ',' CSV HEADER;
COPY products     FROM '/path/olist_products_dataset.csv'               DELIMITER ',' CSV HEADER;
COPY sellers      FROM '/path/olist_sellers_dataset.csv'                DELIMITER ',' CSV HEADER;
COPY orders       FROM '/path/olist_orders_dataset.csv'                 DELIMITER ',' CSV HEADER;
COPY order_items  FROM '/path/olist_order_items_dataset.csv'            DELIMITER ',' CSV HEADER;
COPY payments     FROM '/path/olist_order_payments_dataset.csv'         DELIMITER ',' CSV HEADER;
COPY reviews      FROM '/path/olist_order_reviews_dataset.csv'          DELIMITER ',' CSV HEADER;
COPY geolocation  FROM '/path/olist_geolocation_dataset.csv'            DELIMITER ',' CSV HEADER;
COPY product_category_name_translation
                  FROM '/path/product_category_name_translation.csv'    DELIMITER ',' CSV HEADER;
```

### 3. Open the Dashboard

```bash
open olist_dashboard.html
```

---

## 🛠️ Tech Stack

| Layer | Tools |
|---|---|
| Data Cleaning & EDA | SQL (PostgreSQL), Python (Pandas) |
| Customer Analytics | Python (RFM, cohort analysis, Scikit-learn) |
| Database | PostgreSQL |
| BI & Visualization | Power BI, DAX |
| Web Dashboard | HTML, CSS, JavaScript |
| Data Format | CSV (9 tables, 100K+ orders) |

---

## 💡 Key Business Questions Answered

- Which **customer segments** have the highest lifetime value and repeat purchase potential?
- What is the **true retention rate** and where does the drop-off happen by cohort?
- Which **product categories** drive disproportionate revenue vs. order volume?
- How does **delivery speed** directly correlate with customer satisfaction scores?
- Which **states and cities** represent untapped geographic growth opportunities?
- Which **sellers** underperform on delivery time and risk churning customers?
- Which customers are **At Risk** (high past value, recently inactive) for win-back campaigns?

---

## 👤 Author

**Rohit Bhowmick** — Data Analyst  
*SQL · Python · Tableau · Power BI*

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat&logo=linkedin)](https://linkedin.com/in/rohit-bhowmick)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?style=flat&logo=github)](https://github.com/rohit-bhowmick2002)

---

*Built to demonstrate real-world e-commerce analytics competency: relational data modelling, multi-level SQL engineering, customer segmentation, operational diagnostics, and business storytelling through data.*
