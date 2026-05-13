-- create Customers Table

CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT,
    customer_zip_code_prefix INT,
    customer_city TEXT,
    customer_state TEXT
);
select * from customers;

-- create Orders Table

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    order_status TEXT,
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);
select * from orders;

-- create Order Items Table

CREATE TABLE order_items (
    order_id TEXT,
    order_item_id INT,
    product_id TEXT,
    seller_id TEXT,
    shipping_limit_date TIMESTAMP,
    price NUMERIC,
    freight_value NUMERIC
);
select * from order_items;

-- create Products Table

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_category_name TEXT,
    product_name_length INT,
    product_description_length INT,
    product_photos_qty INT,
    product_weight_g INT,
    product_length_cm INT,
    product_height_cm INT,
    product_width_cm INT
);
select * from products;

-- create Sellers Table

CREATE TABLE sellers (
    seller_id TEXT PRIMARY KEY,
    seller_zip_code_prefix INT,
    seller_city TEXT,
    seller_state TEXT
);
select * from sellers;

-- create Payments Table

CREATE TABLE payments (
    order_id TEXT,
    payment_sequential INT,
    payment_type TEXT,
    payment_installments INT,
    payment_value NUMERIC
);
select * from payments;

-- create Reviews Table

CREATE TABLE reviews (
    review_id TEXT PRIMARY KEY,
    order_id TEXT,
    review_score INT,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP
);
select * from reviews;

-- create Geolocation Table

CREATE TABLE geolocation (
    geolocation_zip_code_prefix INT,
    geolocation_lat NUMERIC,
    geolocation_lng NUMERIC,
    geolocation_city TEXT,
    geolocation_state TEXT
);
r

-- create product_category_name_translation table

CREATE TABLE product_category_name_translation (
    product_category_name TEXT PRIMARY KEY,
    product_category_name_english TEXT
);
select * from product_category_name_translation;




-- LEVEL 1: Basic Business Metrics

-- 1️ :total Orders & Revenue
-- Question: What is the total number of orders and total revenue?

SELECT 
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(payment_value)::numeric, 2) AS total_revenue
FROM payments;



-- 2 :Monthly Revenue Trend

SELECT 
    DATE_TRUNC('month', o.order_purchase_timestamp) AS month,
    ROUND(SUM(p.payment_value)::numeric, 2) AS revenue
FROM orders o
JOIN payments p ON o.order_id = p.order_id
GROUP BY month
ORDER BY month;



-- LEVEL 2: Customer Analysis

-- 3 :Top Customers by Spending

SELECT 
    c.customer_unique_id,
    ROUND(SUM(p.payment_value)::numeric, 2) AS total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN payments p ON o.order_id = p.order_id
GROUP BY c.customer_unique_id
ORDER BY total_spent DESC
LIMIT 10;



-- 4: Customer Retention Rate

SELECT 
    COUNT(*) FILTER (WHERE order_count > 1) * 100.0 / COUNT(*) AS retention_rate
FROM (
    SELECT 
        c.customer_unique_id,
        COUNT(o.order_id) AS order_count
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_unique_id
) t;



-- LEVEL 3: Delivery Analysis
-- 5 :Average Delivery Time

SELECT 
    AVG(order_delivered_customer_date - order_purchase_timestamp) AS avg_delivery_time
FROM orders
WHERE order_delivered_customer_date IS NOT NULL;



-- 6 : Late Deliveries

SELECT 
    COUNT(*) AS late_orders
FROM orders
WHERE order_delivered_customer_date > order_estimated_delivery_date;



-- LEVEL 4: Reviews Analysis
-- 7 : Average Review Score

SELECT ROUND(AVG(review_score), 2) AS avg_rating
FROM reviews;



-- 8 :Delivery Time vs Rating

SELECT 
    r.review_score,
    AVG(o.order_delivered_customer_date - o.order_purchase_timestamp) AS avg_delivery_time
FROM reviews r
JOIN orders o ON r.order_id = o.order_id
GROUP BY r.review_score
ORDER BY r.review_score;



-- LEVEL 5: Revenue Insights
-- 9 :Top Categories by Revenue

SELECT 
    t.product_category_name_english,
    ROUND(SUM(oi.price + oi.freight_value)::numeric, 2) AS revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
JOIN product_category_name_translation t 
    ON p.product_category_name = t.product_category_name
GROUP BY t.product_category_name_english
ORDER BY revenue DESC
LIMIT 10;



-- 10 : Average Order Value (AOV)

SELECT 
    ROUND(SUM(payment_value)::numeric / COUNT(DISTINCT order_id), 2) AS avg_order_value
FROM payments;



-- LEVEL 6: Location Analysis
-- 11 :Top Cities by Orders

SELECT 
    c.customer_city,
    COUNT(o.order_id) AS total_orders
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_city
ORDER BY total_orders DESC
LIMIT 10;



-- 12 : Revenue by State

SELECT 
    c.customer_state,
    ROUND(SUM(p.payment_value)::numeric, 2) AS revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN payments p ON o.order_id = p.order_id
GROUP BY c.customer_state
ORDER BY revenue DESC;



-- LEVEL 7: Seller Analysis
-- 13 : Top Sellers by Revenue

SELECT 
    seller_id,
    ROUND(SUM(price)::numeric, 2) AS revenue
FROM order_items
GROUP BY seller_id
ORDER BY revenue DESC
LIMIT 10;



-- 14 : Seller Delivery Speed

SELECT 
    oi.seller_id,
    AVG(o.order_delivered_customer_date - o.order_purchase_timestamp) AS avg_delivery_time
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
GROUP BY oi.seller_id
ORDER BY avg_delivery_time;



-- LEVEL 8: Problem Detection
-- 15 :High Freight Cost Orders

SELECT 
    order_id,
    SUM(freight_value) AS total_freight
FROM order_items
GROUP BY order_id
ORDER BY total_freight DESC
LIMIT 10;



-- 16 : Cancellation Rate

SELECT 
    COUNT(*) FILTER (WHERE order_status = 'canceled') * 100.0 
    / COUNT(*) AS cancellation_rate
FROM orders;



-- LEVEL 9: Time Analysis
-- 17 : Peak Order Hour

SELECT 
    EXTRACT(HOUR FROM order_purchase_timestamp) AS hour,
    COUNT(*) AS total_orders
FROM orders
GROUP BY hour
ORDER BY total_orders DESC;



-- 18 : Weekend vs Weekday Revenue

SELECT 
    CASE 
        WHEN EXTRACT(DOW FROM order_purchase_timestamp) IN (0,6) THEN 'Weekend'
        ELSE 'Weekday'
    END AS day_type,
    ROUND(SUM(p.payment_value)::numeric, 2) AS revenue
FROM orders o
JOIN payments p ON o.order_id = p.order_id
GROUP BY day_type;



-- LEVEL 10: Window Functions
-- 19 : Running Revenue

SELECT 
    DATE_TRUNC('month', o.order_purchase_timestamp) AS month,
    SUM(p.payment_value) AS monthly_revenue,
    SUM(SUM(p.payment_value)) OVER (ORDER BY DATE_TRUNC('month', o.order_purchase_timestamp)) AS cumulative_revenue
FROM orders o
JOIN payments p ON o.order_id = p.order_id
GROUP BY month
ORDER BY month;



-- 20: Top Product per Category

SELECT *
FROM (
    SELECT 
        p.product_category_name,
        oi.product_id,
        COUNT(*) AS total_sold,
        RANK() OVER (PARTITION BY p.product_category_name ORDER BY COUNT(*) DESC) AS rank
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    GROUP BY p.product_category_name, oi.product_id
) t
WHERE rank = 1;



-- LEVEL 11: Advanced Business Logic
-- 21: Low Rated Products

SELECT 
    oi.product_id,
    ROUND(AVG(r.review_score), 2) AS avg_rating
FROM order_items oi
JOIN reviews r ON oi.order_id = r.order_id
GROUP BY oi.product_id
HAVING AVG(r.review_score) < 3
ORDER BY avg_rating;



-- 22 : Repeat Customers

SELECT 
    c.customer_unique_id,
    COUNT(o.order_id) AS total_orders
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_unique_id
ORDER BY total_orders DESC;



-- LEVEL 12: EXPERT 
-- 23 : RFM Analysis

SELECT 
    c.customer_unique_id,
    MAX(o.order_purchase_timestamp) AS last_purchase,
    COUNT(o.order_id) AS frequency,
    SUM(p.payment_value) AS monetary
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN payments p ON o.order_id = p.order_id
GROUP BY c.customer_unique_id;



-- 24 : Customer Lifetime Value (CLTV)

SELECT 
    c.customer_unique_id,
    ROUND(SUM(p.payment_value)::numeric, 2) AS lifetime_value
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN payments p ON o.order_id = p.order_id
GROUP BY c.customer_unique_id
ORDER BY lifetime_value DESC;