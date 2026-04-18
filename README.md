# Sales & Profit - SQL Data Analysis Project

A end-to-end data analysis project using **SQLite + Python**, exploring customer behavior, product performance, and business health across 170,000+ records

---

## 📊 Dataset

| File | Rows | Description |
|---|---|---|
| `users.csv` | 10,000 | Customer profiles (name, city, signup date) |
| `products.csv` | 2,000 | Product catalog (category, brand, price, rating) |
| `orders.csv` | 20,000 | Order headers (date, status, total amount) |
| `order_items.csv` | 43,525 | Line items per order (quantity, price) |
| `reviews.csv` | 15,000 | Customer reviews (rating, text, date) |
| `events.csv` | 80,000 | Behavioral events (view, wishlist, cart, purchase) |

**Data Quality:** 0 NULLs on key columns, 0 duplicates, 0 orphan foreign keys across all 6 tables

---

## Project Structure

```
Sales & Profit/
├── setup_and_analysis.py    # Phase 1: DB setup + data quality checks
├── analysis.py              # Phase 2: All 5 SQL analyses
├── visualize.py             # Phase 3: Charts 
└── README.md
```

---

## How to Run

```bash
# 1. Install dependencies
`pip install pandas matplotlib seaborn`

# 2. Setup database & run quality checks
`python setup_and_analysis.py`

# 3. Run all SQL analyses
`python analysis.py`

# 4. Generate charts
`python visualize.py`
```

---

## 1. Customer Journey & Funnel

**Goal:** Track user drop-off from first product view to completed order.

**Results:**

| Stage | Count | Conversion vs View |
|---|---|---|
| View | 56,013 | 100% |
| Cart | 12,035 | 21.5% |
| Wishlist | 7,946 | 14.2% |
| Purchase | 4,006 | 7.2% |
| Completed Order | 4,021 | 7.2% |



**Findings:**
- The biggest drop-off is View → Cart (only 21.5% proceed). This is the highest-leverage point for UX optimization.
- Wishlist-to-purchase conversion is low — wishlist feature may not be driving intent effectively.
- Purchase and Completed Order counts are nearly identical, meaning fulfillment/cancellation is not a major issue.

**Business Recommendations:**
- A/B test product page CTAs and "Add to Cart" button placement.
- Trigger cart abandonment emails within 1 hour of cart add.
- Consider removing or redesigning the wishlist flow if it's not converting.

---

## Analysis 2 — RFM Customer Segmentation

**Goal:** Classify customers by Recency, Frequency, and Monetary value to prioritize marketing spend.

```sql
WITH ref_date AS (SELECT DATE(MAX(order_date)) AS max_date FROM orders),
rfm_raw AS (
    SELECT user_id,
           CAST(JULIANDAY((SELECT max_date FROM ref_date)) - JULIANDAY(MAX(order_date)) AS INT) AS recency,
           COUNT(DISTINCT order_id)  AS frequency,
           SUM(total_amount)         AS monetary
    FROM orders
    WHERE order_status IN ('completed','processing','shipped')
    GROUP BY user_id
),
rfm_scored AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency DESC)  AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)  AS m_score
    FROM rfm_raw
)
SELECT *,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'New Customers'
        WHEN r_score <= 2 AND f_score >= 4 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost'
        ELSE 'Potential Loyalists'
    END AS segment
FROM rfm_scored;
```

**Results:**

| Segment | Customers | Avg Recency (days) | Avg Orders | Avg Revenue |
|---|---|---|---|---|
| Lost | 1,554 | 500 | 1.0 | $273 |
| Champions | 1,547 | 84 | 2.7 | $1,821 |
| Loyal Customers | 1,399 | 187 | 2.0 | $1,237 |
| Potential Loyalists | 1,109 | 378 | 1.1 | $882 |
| New Customers | 731 | 95 | 1.0 | $271 |
| At Risk | 632 | 422 | 2.3 | $1,653 |

**Findings:**
- "At Risk" customers average $1,653 revenue — nearly as high as Champions. They've bought frequently but haven't returned in 422 days on average.
- "Lost" is the largest segment (1,554 customers) but lowest value — low ROI to re-engage.
- "New Customers" and "Lost" have similar avg revenue ($271–$273), confirming most one-time buyers never return.

**Business Recommendations:**
- Launch a win-back campaign targeting "At Risk" with a personalized discount (high ROI given their revenue history).
- Nurture "Potential Loyalists" with loyalty points or early access to new products.
- Don't over-invest in "Lost" — focus budget on Champions and At Risk.

---

## Analysis 3 — Product & Category Performance

**Goal:** Identify which categories and products drive the most revenue to guide sourcing and marketing decisions.

```sql
SELECT
    p.category,
    COUNT(DISTINCT oi.order_id)          AS total_orders,
    SUM(oi.quantity)                     AS units_sold,
    ROUND(SUM(oi.item_total), 0)         AS total_revenue,
    ROUND(AVG(p.price), 2)               AS avg_price,
    ROUND(AVG(r.rating), 2)              AS avg_review_rating
FROM order_items oi
JOIN products p  ON oi.product_id = p.product_id
LEFT JOIN reviews r ON oi.product_id = r.product_id
GROUP BY p.category
ORDER BY total_revenue DESC;
```

**Results:**

| Category | Revenue | Units Sold | Avg Price | Avg Rating |
|---|---|---|---|---|
| Electronics | $37.8M | 44,527 | $848 | 3.55 |
| Automotive | $19.1M | 44,595 | $430 | 3.52 |
| Home & Kitchen | $8.6M | 44,833 | $189 | 3.54 |
| Sports | $7.5M | 44,809 | $167 | 3.53 |
| Clothing | $5.6M | 50,343 | $112 | 3.55 |
| Beauty | $4.5M | 51,471 | $88 | 3.57 |
| Toys | $3.2M | 53,198 | $59 | 3.55 |
| Pet Supplies | $2.8M | 53,158 | $53 | 3.59 |
| Books | $2.2M | 48,798 | $46 | 3.54 |
| Groceries | $676K | 41,313 | $16 | 3.53 |

**Findings:**
- Electronics alone accounts for ~47% of total revenue despite similar unit volumes to other categories — purely driven by high average price ($848).
- Groceries has the lowest revenue despite reasonable unit volume — very low margin category.
- Ratings are nearly identical across all categories (3.52–3.59), suggesting no category has a quality differentiation advantage.

**Business Recommendations:**
- Double down on Electronics inventory and marketing — highest revenue leverage per unit.
- For Groceries, consider whether the category is worth maintaining or should be repositioned as a traffic driver.
- Since ratings are flat across categories, focus on review volume (social proof) rather than chasing higher scores.

---

## Analysis 4 — Cohort Retention

**Goal:** Measure how well the platform retains customers after their first purchase.

```sql
WITH first_order AS (
    SELECT user_id, STRFTIME('%Y-%m', MIN(order_date)) AS cohort_month
    FROM orders WHERE order_status IN ('completed','processing','shipped')
    GROUP BY user_id
),
order_activity AS (
    SELECT o.user_id, fo.cohort_month,
           (CAST(STRFTIME('%Y', o.order_date) AS INT) - CAST(STRFTIME('%Y', fo.cohort_month||'-01') AS INT)) * 12
           + (CAST(STRFTIME('%m', o.order_date) AS INT) - CAST(STRFTIME('%m', fo.cohort_month||'-01') AS INT)) AS month_number
    FROM orders o JOIN first_order fo ON o.user_id = fo.user_id
    WHERE o.order_status IN ('completed','processing','shipped')
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT user_id) AS cohort_users FROM first_order GROUP BY cohort_month
),
retention_raw AS (
    SELECT cohort_month, month_number, COUNT(DISTINCT user_id) AS active_users
    FROM order_activity GROUP BY cohort_month, month_number
)
SELECT r.cohort_month, r.month_number, r.active_users, cs.cohort_users,
       ROUND(100.0 * r.active_users / cs.cohort_users, 1) AS retention_pct
FROM retention_raw r JOIN cohort_size cs ON r.cohort_month = cs.cohort_month
WHERE r.month_number BETWEEN 0 AND 6
ORDER BY r.cohort_month, r.month_number;
```

**Results (sample — Jan 2024 cohort, 512 customers):**

| Month | Active Users | Retention % |
|---|---|---|
| 0 (first purchase) | 512 | 100% |
| 1 | 28 | 5.5% |
| 2 | 28 | 5.5% |
| 3 | 21 | 4.1% |
| 4 | 15 | 2.9% |
| 5 | 24 | 4.7% |
| 6 | 29 | 5.7% |

**Findings:**
- Month-1 retention is only ~5% across all cohorts — critically low. The platform loses 95% of customers after their first order.
- Retention stabilizes at 3–6% from month 2 onward, suggesting a small loyal core but no meaningful re-engagement.
- No cohort shows improvement over time, meaning the problem is structural, not seasonal.

**Business Recommendations:**
- Implement a post-purchase email sequence: order confirmation → delivery follow-up → "You might also like" at day 14 → discount at day 30.
- Introduce a loyalty/points program to incentivize second purchases.
- Investigate whether the product catalog has enough repeat-purchase categories (Groceries, Beauty) to drive natural retention.

---

## Analysis 5 — Reviews Impact on Sales & Returns

**Goal:** Understand whether review ratings actually drive sales volume and return rates.

```sql
WITH product_stats AS (
    SELECT p.product_id, p.category,
           ROUND(AVG(r.rating), 2)      AS avg_rating,
           COUNT(r.review_id)           AS review_count,
           SUM(oi.quantity)             AS units_sold,
           ROUND(SUM(oi.item_total), 0) AS revenue
    FROM products p
    LEFT JOIN reviews r  ON p.product_id = r.product_id
    LEFT JOIN order_items oi ON p.product_id = oi.product_id
    GROUP BY p.product_id HAVING review_count > 0
)
SELECT
    CASE
        WHEN avg_rating >= 4.5 THEN '5star (4.5-5.0)'
        WHEN avg_rating >= 4.0 THEN '4star (4.0-4.4)'
        WHEN avg_rating >= 3.0 THEN '3star (3.0-3.9)'
        ELSE '1-2star (<3.0)'
    END AS rating_band,
    COUNT(*)                    AS product_count,
    ROUND(AVG(units_sold), 0)   AS avg_units_sold,
    ROUND(AVG(revenue), 0)      AS avg_revenue
FROM product_stats
GROUP BY rating_band ORDER BY avg_revenue DESC;
```

**Results:**

| Rating Band | Products | Avg Units Sold | Avg Revenue | Return Rate |
|---|---|---|---|---|
| 3star (3.0–3.9) | 1,506 | 254 | $48,753 | 22.1% |
| 4star (4.0–4.4) | 324 | 205 | $41,998 | 22.4% |
| 1-2star (<3.0) | 142 | 180 | $31,792 | 20.9% |
| 5star (4.5–5.0) | 27 | 115 | $13,272 | 22.0% |

**Findings:**
- Counter-intuitive: 3-star products generate the highest average revenue ($48,753) and sell the most units. This is partly because there are far more 3-star products (1,506 vs 27 five-star products).
- Return rate is nearly identical across all rating bands (~21–22%), meaning customer satisfaction scores do NOT predict returns. Returns are likely driven by logistics, sizing, or expectation mismatch — not product quality.
- Very few products achieve 5-star status (only 27), and they sell fewer units — possibly niche or premium items.

**Business Recommendations:**
- Don't suppress or hide 3-star products — they are your volume drivers.
- Investigate return reasons independently of ratings (add a return reason field to the data model).
- Focus review strategy on increasing review *volume* rather than chasing higher scores, as volume correlates with sales.

---

## Key Business Takeaways

| Priority | Finding | Action |
|---|---|---|
| High | 95% of customers never return after first purchase | Build post-purchase email sequence + loyalty program |
| High | View-to-Cart conversion is only 21.5% | Optimize product page UX and CTAs |
| High | "At Risk" segment has $1,653 avg revenue | Launch win-back campaign immediately |
| Medium | Electronics = 47% of revenue | Prioritize Electronics inventory and ads |
| Low | Return rate is flat regardless of rating | Investigate logistics/fulfillment as root cause of returns |

---

## Tech Stack

- **Database:** SQLite 3
- **Language:** Python 3.11
- **Libraries:** pandas, matplotlib, seaborn
- **SQL Features used:** CTEs, Window Functions (NTILE, OVER), JULIANDAY, STRFTIME, CASE WHEN, subqueries
