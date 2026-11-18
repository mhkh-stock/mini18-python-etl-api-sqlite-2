-- Mini #18 — analysis queries (run: python3 src/run_queries.py).
-- 10 questions over the loaded DummyJSON product catalogue.
-- Each query is numbered and states its question in the comment
-- above it. Run them against data/products.db.

-- Q1. Which categories hold the most stock value?
--     (stock value = price x stock, summed per category)
SELECT category,
       COUNT(*) AS products,
       ROUND(SUM(price * stock), 2) AS stock_value_usd,
       ROUND(AVG(price), 2) AS avg_price_usd,
       ROUND(AVG(rating), 2) AS avg_rating
FROM fact_product
GROUP BY category
ORDER BY stock_value_usd DESC;

-- Q2. Which categories are the most expensive on average?
SELECT category,
       COUNT(*) AS products,
       ROUND(MIN(price), 2) AS min_price_usd,
       ROUND(AVG(price), 2) AS avg_price_usd,
       ROUND(MAX(price), 2) AS max_price_usd
FROM fact_product
GROUP BY category
ORDER BY avg_price_usd DESC;

-- Q3. What are the 10 most expensive products in the catalogue?
SELECT product_id, title, category, brand,
       price AS price_usd,
       discount_pct,
       ROUND(price * (1 - discount_pct / 100.0), 2) AS price_after_discount_usd,
       stock
FROM fact_product
ORDER BY price DESC
LIMIT 10;

-- Q4. Where are the biggest discounts?
--     Average discount by category, plus the single deepest cut.
SELECT category,
       COUNT(*) AS products,
       ROUND(AVG(discount_pct), 2) AS avg_discount_pct,
       ROUND(MAX(discount_pct), 2) AS max_discount_pct
FROM fact_product
GROUP BY category
ORDER BY avg_discount_pct DESC;

-- Q5. Which products are running low on stock?
--     Out of stock first, then the 10 lowest positive stock levels.
SELECT product_id, title, category, brand, stock, price AS price_usd,
       availability
FROM fact_product
ORDER BY stock ASC, price DESC
LIMIT 15;

-- Q6. Which brands carry the catalogue?
--     Products per brand and each brand's average price and rating.
SELECT brand,
       COUNT(*) AS products,
       ROUND(AVG(price), 2) AS avg_price_usd,
       ROUND(AVG(rating), 2) AS avg_rating,
       SUM(stock) AS total_stock
FROM fact_product
WHERE brand IS NOT NULL
GROUP BY brand
ORDER BY products DESC, avg_price_usd DESC;

-- Q7. How are product ratings distributed?
--     Buckets: under 3, 3-4, 4-4.5, 4.5 and above.
SELECT CASE
         WHEN rating < 3 THEN 'under 3.0'
         WHEN rating < 4 THEN '3.0 - 3.9'
         WHEN rating < 4.5 THEN '4.0 - 4.4'
         ELSE '4.5 and above'
       END AS rating_bucket,
       COUNT(*) AS products,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM fact_product), 1)
         AS pct_of_catalogue
FROM fact_product
GROUP BY rating_bucket
ORDER BY rating_bucket;

-- Q8. Do pricier products rate better?
--     Average rating by price band.
SELECT CASE
         WHEN price < 10 THEN 'under $10'
         WHEN price < 50 THEN '$10 - $49'
         WHEN price < 200 THEN '$50 - $199'
         WHEN price < 1000 THEN '$200 - $999'
         ELSE '$1000 and above'
       END AS price_band,
       COUNT(*) AS products,
       ROUND(AVG(rating), 2) AS avg_rating,
       ROUND(AVG(discount_pct), 2) AS avg_discount_pct
FROM fact_product
GROUP BY price_band
ORDER BY MIN(price);

-- Q9. What are the most common tags in the catalogue?
SELECT tag, COUNT(*) AS products
FROM bridge_product_tag
GROUP BY tag
ORDER BY products DESC, tag ASC
LIMIT 15;

-- Q10. Do customer reviews agree with the listed product rating?
--      Products where the average review rating is furthest from
--      the rating the catalogue lists (only products with reviews).
SELECT p.product_id,
       p.title,
       p.rating AS listed_rating,
       COUNT(r.review_id) AS reviews,
       ROUND(AVG(r.rating), 2) AS avg_review_rating,
       ROUND(AVG(r.rating) - p.rating, 2) AS review_minus_listed
FROM fact_product p
JOIN fact_review r ON r.product_id = p.product_id
GROUP BY p.product_id, p.title, p.rating
ORDER BY ABS(review_minus_listed) DESC
LIMIT 10;
