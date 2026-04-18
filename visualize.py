import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import numpy as np
import os, warnings
warnings.filterwarnings("ignore")

DATA_DIR = r"C:\Users\X1 Carbon Gen 9\Documents\Data Analys\Sales & Profit"
DB_PATH  = os.path.join(DATA_DIR, "sales_profit.db")
OUT_DIR  = os.path.join(DATA_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({"figure.dpi": 130, "font.size": 10})

conn = sqlite3.connect(DB_PATH)

# ─── CHART 1: FUNNEL ─────────────────────────────────────────────────────────
sql_funnel = """
WITH ec AS (
    SELECT
        SUM(CASE WHEN event_type='view'     THEN 1 ELSE 0 END) AS views,
        SUM(CASE WHEN event_type='wishlist' THEN 1 ELSE 0 END) AS wishlists,
        SUM(CASE WHEN event_type='cart'     THEN 1 ELSE 0 END) AS carts,
        SUM(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END) AS purchases
    FROM events
),
oc AS (SELECT COUNT(DISTINCT order_id) AS completed FROM orders WHERE order_status='completed')
SELECT 'View'            AS stage, views      AS cnt FROM ec UNION ALL
SELECT 'Wishlist',        wishlists FROM ec UNION ALL
SELECT 'Cart',            carts     FROM ec UNION ALL
SELECT 'Purchase',        purchases FROM ec UNION ALL
SELECT 'Completed Order', completed FROM oc;
"""
df_f = pd.read_sql(sql_funnel, conn)
df_f["conv"] = (df_f["cnt"] / df_f["cnt"].iloc[0] * 100).round(1)

fig, ax = plt.subplots(figsize=(9, 5))
colors = sns.color_palette("Blues_d", len(df_f))[::-1]
bars = ax.barh(df_f["stage"][::-1], df_f["cnt"][::-1], color=colors)
for bar, conv in zip(bars, df_f["conv"][::-1]):
    ax.text(bar.get_width() + 300, bar.get_y() + bar.get_height()/2,
            f'{bar.get_width():,.0f}  ({conv}%)', va='center', fontsize=9)
ax.set_xlabel("Event Count")
ax.set_title("Ideal 1 — Customer Journey Funnel", fontweight="bold", pad=12)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
ax.set_xlim(0, df_f["cnt"].max() * 1.25)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "ideal1_funnel.png"))
plt.close()
print("Saved ideal1_funnel.png")

# ─── CHART 2: RFM SEGMENTS ───────────────────────────────────────────────────
sql_rfm = """
WITH ref AS (SELECT DATE(MAX(order_date)) AS mx FROM orders),
raw AS (
    SELECT user_id,
           CAST(JULIANDAY((SELECT mx FROM ref)) - JULIANDAY(MAX(order_date)) AS INT) AS recency,
           COUNT(DISTINCT order_id) AS frequency,
           SUM(total_amount)        AS monetary
    FROM orders WHERE order_status IN ('completed','processing','shipped')
    GROUP BY user_id
),
sc AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency DESC)  AS r,
        NTILE(5) OVER (ORDER BY frequency ASC) AS f,
        NTILE(5) OVER (ORDER BY monetary ASC)  AS m
    FROM raw
)
SELECT *,
    CASE
        WHEN r>=4 AND f>=4 THEN 'Champions'
        WHEN r>=3 AND f>=3 THEN 'Loyal Customers'
        WHEN r>=4 AND f<=2 THEN 'New Customers'
        WHEN r<=2 AND f>=4 THEN 'At Risk'
        WHEN r<=2 AND f<=2 THEN 'Lost'
        ELSE 'Potential Loyalists'
    END AS segment
FROM sc;
"""
df_rfm_full = pd.read_sql(sql_rfm, conn)
seg_summary = df_rfm_full.groupby("segment").agg(
    count=("user_id","count"),
    avg_revenue=("monetary","mean")
).reset_index().sort_values("count", ascending=False)

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
palette = sns.color_palette("Set2", len(seg_summary))

axes[0].pie(seg_summary["count"], labels=seg_summary["segment"],
            autopct="%1.1f%%", colors=palette, startangle=140,
            textprops={"fontsize": 9})
axes[0].set_title("Customer Distribution by Segment", fontweight="bold")

sns.barplot(data=seg_summary, x="segment", y="avg_revenue", palette=palette, ax=axes[1])
axes[1].set_title("Avg Revenue per Segment", fontweight="bold")
axes[1].set_xlabel("")
axes[1].set_ylabel("Avg Revenue (USD)")
axes[1].tick_params(axis="x", rotation=25)
axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))
for p in axes[1].patches:
    axes[1].annotate(f'${p.get_height():,.0f}',
                     (p.get_x() + p.get_width()/2, p.get_height()),
                     ha='center', va='bottom', fontsize=8)

plt.suptitle("Ideal 2 — RFM Customer Segmentation", fontweight="bold", y=1.01)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "ideal2_rfm.png"), bbox_inches="tight")
plt.close()
print("Saved ideal2_rfm.png")

# ─── CHART 3: CATEGORY PERFORMANCE ──────────────────────────────────────────
sql_cat = """
SELECT p.category,
       ROUND(SUM(oi.item_total),0) AS revenue,
       SUM(oi.quantity)            AS units_sold,
       ROUND(AVG(r.rating),2)      AS avg_rating
FROM order_items oi
JOIN products p ON oi.product_id=p.product_id
LEFT JOIN reviews r ON oi.product_id=r.product_id
GROUP BY p.category ORDER BY revenue DESC;
"""
df_cat = pd.read_sql(sql_cat, conn)

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
pal = sns.color_palette("muted", len(df_cat))

sns.barplot(data=df_cat, x="revenue", y="category", palette=pal, ax=axes[0])
axes[0].set_title("Revenue by Category", fontweight="bold")
axes[0].set_xlabel("Total Revenue (USD)")
axes[0].xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x/1e6:.1f}M'))
for p in axes[0].patches:
    axes[0].annotate(f'${p.get_width()/1e6:.1f}M',
                     (p.get_width(), p.get_y() + p.get_height()/2),
                     ha='left', va='center', fontsize=8, xytext=(4,0), textcoords='offset points')

ax2 = axes[1]
x = np.arange(len(df_cat))
w = 0.4
b1 = ax2.bar(x - w/2, df_cat["units_sold"], w, label="Units Sold", color=sns.color_palette("Blues_d", 1)[0])
ax2b = ax2.twinx()
ax2b.plot(x, df_cat["avg_rating"], "o-", color="tomato", label="Avg Rating", linewidth=2)
ax2.set_xticks(x); ax2.set_xticklabels(df_cat["category"], rotation=30, ha="right", fontsize=8)
ax2.set_ylabel("Units Sold"); ax2b.set_ylabel("Avg Rating")
ax2b.set_ylim(3.0, 4.0)
ax2.set_title("Units Sold & Avg Rating by Category", fontweight="bold")
lines1, labels1 = ax2.get_legend_handles_labels()
lines2, labels2 = ax2b.get_legend_handles_labels()
ax2.legend(lines1+lines2, labels1+labels2, loc="upper right", fontsize=8)

plt.suptitle("Ideal 3 — Product & Category Performance", fontweight="bold", y=1.01)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "ideal3_category.png"), bbox_inches="tight")
plt.close()
print("Saved ideal3_category.png")

# ─── CHART 4: COHORT RETENTION HEATMAP ───────────────────────────────────────
sql_cohort = """
WITH fo AS (
    SELECT user_id, STRFTIME('%Y-%m', MIN(order_date)) AS cohort
    FROM orders WHERE order_status IN ('completed','processing','shipped')
    GROUP BY user_id
),
act AS (
    SELECT o.user_id, fo.cohort,
           (CAST(STRFTIME('%Y',o.order_date) AS INT) - CAST(STRFTIME('%Y',fo.cohort||'-01') AS INT))*12
           + CAST(STRFTIME('%m',o.order_date) AS INT) - CAST(STRFTIME('%m',fo.cohort||'-01') AS INT) AS mn
    FROM orders o JOIN fo ON o.user_id=fo.user_id
    WHERE o.order_status IN ('completed','processing','shipped')
),
cs AS (SELECT cohort, COUNT(DISTINCT user_id) AS sz FROM fo GROUP BY cohort),
rr AS (SELECT cohort, mn, COUNT(DISTINCT user_id) AS au FROM act GROUP BY cohort, mn)
SELECT r.cohort, r.mn, ROUND(100.0*r.au/cs.sz,1) AS pct
FROM rr r JOIN cs ON r.cohort=cs.cohort
WHERE r.mn BETWEEN 0 AND 5
ORDER BY r.cohort, r.mn;
"""
df_c = pd.read_sql(sql_cohort, conn)
pivot = df_c.pivot(index="cohort", columns="mn", values="pct")
pivot.columns = [f"Month {c}" for c in pivot.columns]

fig, ax = plt.subplots(figsize=(11, 7))
mask = pivot.isna()
sns.heatmap(pivot, annot=True, fmt=".1f", cmap="YlOrRd_r",
            linewidths=0.5, ax=ax, mask=mask,
            cbar_kws={"label": "Retention %"})
ax.set_title("Ideal 4 — Cohort Retention Heatmap (%)", fontweight="bold", pad=12)
ax.set_xlabel("Month Since First Order")
ax.set_ylabel("Cohort (First Order Month)")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "ideal4_cohort.png"))
plt.close()
print("Saved ideal4_cohort.png")

# ─── CHART 5: REVIEWS IMPACT ─────────────────────────────────────────────────
sql_rev = """
WITH ps AS (
    SELECT p.product_id,
           ROUND(AVG(r.rating),2) AS avg_rating,
           COUNT(r.review_id)     AS rcnt,
           SUM(oi.quantity)       AS units,
           ROUND(SUM(oi.item_total),0) AS rev
    FROM products p
    LEFT JOIN reviews r ON p.product_id=r.product_id
    LEFT JOIN order_items oi ON p.product_id=oi.product_id
    GROUP BY p.product_id HAVING rcnt>0
)
SELECT CASE
    WHEN avg_rating>=4.5 THEN '5star (4.5-5.0)'
    WHEN avg_rating>=4.0 THEN '4star (4.0-4.4)'
    WHEN avg_rating>=3.0 THEN '3star (3.0-3.9)'
    ELSE '1-2star (<3.0)'
END AS band,
COUNT(*) AS products, ROUND(AVG(units),0) AS avg_units, ROUND(AVG(rev),0) AS avg_rev
FROM ps GROUP BY band ORDER BY avg_rev DESC;
"""
df_rv = pd.read_sql(sql_rev, conn)

sql_ret = """
SELECT CASE
    WHEN r.rating>=4.5 THEN '5star (4.5-5.0)'
    WHEN r.rating>=4.0 THEN '4star (4.0-4.4)'
    WHEN r.rating>=3.0 THEN '3star (3.0-3.9)'
    ELSE '1-2star (<3.0)'
END AS band,
ROUND(100.0*SUM(CASE WHEN o.order_status='returned' THEN 1 ELSE 0 END)/COUNT(DISTINCT o.order_id),2) AS return_rate
FROM reviews r JOIN orders o ON r.order_id=o.order_id
GROUP BY band ORDER BY return_rate DESC;
"""
df_ret = pd.read_sql(sql_ret, conn)

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
pal5 = sns.color_palette("RdYlGn", len(df_rv))

sns.barplot(data=df_rv, x="band", y="avg_rev", palette=pal5, ax=axes[0])
axes[0].set_title("Avg Revenue by Rating Band", fontweight="bold")
axes[0].set_xlabel("Rating Band"); axes[0].set_ylabel("Avg Revenue (USD)")
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))
for p in axes[0].patches:
    axes[0].annotate(f'${p.get_height():,.0f}',
                     (p.get_x()+p.get_width()/2, p.get_height()),
                     ha='center', va='bottom', fontsize=8)

sns.barplot(data=df_ret, x="band", y="return_rate",
            palette=sns.color_palette("Reds_d", len(df_ret)), ax=axes[1])
axes[1].set_title("Return Rate by Rating Band (%)", fontweight="bold")
axes[1].set_xlabel("Rating Band"); axes[1].set_ylabel("Return Rate (%)")
for p in axes[1].patches:
    axes[1].annotate(f'{p.get_height():.1f}%',
                     (p.get_x()+p.get_width()/2, p.get_height()),
                     ha='center', va='bottom', fontsize=8)

plt.suptitle("Ideal 5 — Reviews Impact on Sales & Returns", fontweight="bold", y=1.01)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "ideal5_reviews.png"), bbox_inches="tight")
plt.close()
print("Saved ideal5_reviews.png")

conn.close()
print("\nAll charts saved to:", OUT_DIR)
