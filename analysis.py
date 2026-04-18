import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import os, warnings
warnings.filterwarnings("ignore")

DATA_DIR = r"C:\Users\X1 Carbon Gen 9\Documents\Data Analys\Sales & Profit"
DB_PATH  = os.path.join(DATA_DIR, "sales_profit.db")
OUT_DIR  = os.path.join(DATA_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({"figure.dpi": 130, "font.size": 10})

conn = sqlite3.connect(DB_PATH)

# ─── IDEAL 1: CUSTOMER JOURNEY & FUNNEL ANALYSIS ─────────────────────────────
print("\n=== IDEAL 1: Customer Journey & Funnel ===")

sql_funnel = """
WITH event_counts AS (
    SELECT
        SUM(CASE WHEN event_type = 'view'     THEN 1 ELSE 0 END) AS views,
        SUM(CASE WHEN event_type = 'wishlist' THEN 1 ELSE 0 END) AS wishlists,
        SUM(CASE WHEN event_type = 'cart'     THEN 1 ELSE 0 END) AS carts,
        SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS purchases
    FROM events
),
order_count AS (
    SELECT COUNT(DISTINCT order_id) AS completed_orders FROM orders
    WHERE order_status = 'completed'
)
SELECT
    'View'             AS stage, views      AS users FROM event_counts
UNION ALL SELECT 'Wishlist', wishlists FROM event_counts
UNION ALL SELECT 'Cart',     carts     FROM event_counts
UNION ALL SELECT 'Purchase', purchases FROM event_counts
UNION ALL SELECT 'Completed Order', completed_orders FROM order_count;
"""
df_funnel = pd.read_sql(sql_funnel, conn)
print(df_funnel.to_string(index=False))

# Conversion rates between stages
df_funnel["conv_rate"] = (df_funnel["users"] / df_funnel["users"].iloc[0] * 100).round(1)
print("\nConversion rates vs View:")
print(df_funnel[["stage","conv_rate"]].to_string(index=False))

# ─── IDEAL 2: RFM SEGMENTATION ───────────────────────────────────────────────
print("\n=== IDEAL 2: RFM Segmentation ===")

sql_rfm = """
WITH ref_date AS (SELECT DATE(MAX(order_date)) AS max_date FROM orders),
rfm_raw AS (
    SELECT
        o.user_id,
        CAST(JULIANDAY((SELECT max_date FROM ref_date)) - JULIANDAY(MAX(o.order_date)) AS INT) AS recency,
        COUNT(DISTINCT o.order_id)  AS frequency,
        SUM(o.total_amount)         AS monetary
    FROM orders o
    WHERE o.order_status IN ('completed','processing','shipped')
    GROUP BY o.user_id
),
rfm_scored AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency DESC)   AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC)  AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)   AS m_score
    FROM rfm_raw
),
rfm_segment AS (
    SELECT *,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2 THEN 'New Customers'
            WHEN r_score <= 2 AND f_score >= 4 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost'
            ELSE 'Potential Loyalists'
        END AS segment
    FROM rfm_scored
)
SELECT segment,
       COUNT(*)                    AS customer_count,
       ROUND(AVG(recency),1)       AS avg_recency_days,
       ROUND(AVG(frequency),1)     AS avg_orders,
       ROUND(AVG(monetary),0)      AS avg_revenue
FROM rfm_segment
GROUP BY segment
ORDER BY customer_count DESC;
"""
df_rfm = pd.read_sql(sql_rfm, conn)
print(df_rfm.to_string(index=False))

# ─── IDEAL 3: PRODUCT & CATEGORY PERFORMANCE ─────────────────────────────────
print("\n=== IDEAL 3: Product & Category Performance ===")

sql_cat = """
SELECT
    p.category,
    COUNT(DISTINCT oi.order_id)          AS total_orders,
    SUM(oi.quantity)                     AS units_sold,
    ROUND(SUM(oi.item_total), 0)         AS total_revenue,
    ROUND(AVG(p.price), 2)               AS avg_price,
    ROUND(AVG(r.rating), 2)              AS avg_review_rating,
    COUNT(DISTINCT r.review_id)          AS review_count
FROM order_items oi
JOIN products p  ON oi.product_id = p.product_id
LEFT JOIN reviews r ON oi.product_id = r.product_id
GROUP BY p.category
ORDER BY total_revenue DESC;
"""
df_cat = pd.read_sql(sql_cat, conn)
print(df_cat.to_string(index=False))

sql_top_products = """
SELECT
    p.product_name,
    p.category,
    SUM(oi.quantity)             AS units_sold,
    ROUND(SUM(oi.item_total),0)  AS revenue,
    ROUND(AVG(r.rating),2)       AS avg_rating
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
LEFT JOIN reviews r ON oi.product_id = r.product_id
GROUP BY p.product_id, p.product_name, p.category
ORDER BY revenue DESC
LIMIT 10;
"""
df_top = pd.read_sql(sql_top_products, conn)
print("\nTop 10 Products by Revenue:")
print(df_top.to_string(index=False))

# ─── IDEAL 4: COHORT RETENTION ───────────────────────────────────────────────
print("\n=== IDEAL 4: Cohort Retention ===")

sql_cohort = """
WITH first_order AS (
    SELECT user_id,
           STRFTIME('%Y-%m', MIN(order_date)) AS cohort_month
    FROM orders
    WHERE order_status IN ('completed','processing','shipped')
    GROUP BY user_id
),
order_activity AS (
    SELECT o.user_id,
           fo.cohort_month,
           STRFTIME('%Y-%m', o.order_date) AS order_month,
           (CAST(STRFTIME('%Y', o.order_date) AS INT) - CAST(STRFTIME('%Y', fo.cohort_month||'-01') AS INT)) * 12
           + (CAST(STRFTIME('%m', o.order_date) AS INT) - CAST(STRFTIME('%m', fo.cohort_month||'-01') AS INT))
           AS month_number
    FROM orders o
    JOIN first_order fo ON o.user_id = fo.user_id
    WHERE o.order_status IN ('completed','processing','shipped')
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT user_id) AS cohort_users
    FROM first_order
    GROUP BY cohort_month
),
retention_raw AS (
    SELECT oa.cohort_month,
           oa.month_number,
           COUNT(DISTINCT oa.user_id) AS active_users
    FROM order_activity oa
    GROUP BY oa.cohort_month, oa.month_number
)
SELECT r.cohort_month,
       r.month_number,
       r.active_users,
       cs.cohort_users,
       ROUND(100.0 * r.active_users / cs.cohort_users, 1) AS retention_pct
FROM retention_raw r
JOIN cohort_size cs ON r.cohort_month = cs.cohort_month
WHERE r.month_number BETWEEN 0 AND 6
ORDER BY r.cohort_month, r.month_number;
"""
df_cohort = pd.read_sql(sql_cohort, conn)
print(df_cohort.head(20).to_string(index=False))

# ─── IDEAL 5: REVIEWS IMPACT ─────────────────────────────────────────────────
print("\n=== IDEAL 5: Reviews Impact ===")

sql_reviews = """
WITH product_stats AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        ROUND(AVG(r.rating), 2)          AS avg_rating,
        COUNT(r.review_id)               AS review_count,
        SUM(oi.quantity)                 AS units_sold,
        ROUND(SUM(oi.item_total), 0)     AS revenue
    FROM products p
    LEFT JOIN reviews r  ON p.product_id = r.product_id
    LEFT JOIN order_items oi ON p.product_id = oi.product_id
    GROUP BY p.product_id, p.product_name, p.category
    HAVING review_count > 0
)
SELECT
    CASE
        WHEN avg_rating >= 4.5 THEN '5star (4.5-5.0)'
        WHEN avg_rating >= 4.0 THEN '4star (4.0-4.4)'
        WHEN avg_rating >= 3.0 THEN '3star (3.0-3.9)'
        ELSE                        '1-2star (<3.0)'
    END AS rating_band,
    COUNT(*)                        AS product_count,
    ROUND(AVG(units_sold), 0)       AS avg_units_sold,
    ROUND(AVG(revenue), 0)          AS avg_revenue,
    ROUND(AVG(review_count), 1)     AS avg_reviews
FROM product_stats
GROUP BY rating_band
ORDER BY avg_revenue DESC;
"""
df_reviews = pd.read_sql(sql_reviews, conn)
print(df_reviews.to_string(index=False))

# Return rate by rating band
sql_return = """
SELECT
    CASE
        WHEN r.rating >= 4.5 THEN '5star (4.5-5.0)'
        WHEN r.rating >= 4.0 THEN '4star (4.0-4.4)'
        WHEN r.rating >= 3.0 THEN '3star (3.0-3.9)'
        ELSE                      '1-2star (<3.0)'
    END AS rating_band,
    COUNT(DISTINCT o.order_id)                                          AS total_orders,
    SUM(CASE WHEN o.order_status = 'returned' THEN 1 ELSE 0 END)       AS returned_orders,
    ROUND(100.0 * SUM(CASE WHEN o.order_status='returned' THEN 1 ELSE 0 END)
          / COUNT(DISTINCT o.order_id), 2)                              AS return_rate_pct
FROM reviews r
JOIN orders o ON r.order_id = o.order_id
GROUP BY rating_band
ORDER BY return_rate_pct DESC;
"""
df_return = pd.read_sql(sql_return, conn)
print("\nReturn Rate by Rating Band:")
print(df_return.to_string(index=False))

conn.close()
print("\n=== ALL SQL ANALYSES COMPLETE ===")
