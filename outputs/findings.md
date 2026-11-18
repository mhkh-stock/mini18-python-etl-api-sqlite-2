# Mini #18 — Findings (2026-11-18)

10 questions over 194 products from the DummyJSON catalogue, loaded into `data/products.db`.

## Q1. Which categories hold the most stock value? (stock value = price x stock, summed per category)

Result: `q01_category_stock_value.csv` (24 rows).

Top row: {'category': 'vehicle', 'products': 5, 'stock_value_usd': 10707996.59, 'avg_price_usd': 31199.99, 'avg_rating': 3.39}

## Q2. Which categories are the most expensive on average?

Result: `q02_category_avg_price.csv` (24 rows).

Top row: {'category': 'vehicle', 'products': 5, 'min_price_usd': 24999.99, 'avg_price_usd': 31199.99, 'max_price_usd': 36999.99}

## Q3. What are the 10 most expensive products in the catalogue?

Result: `q03_top10_most_expensive.csv` (10 rows).

Top row: {'product_id': 170, 'title': 'Durango SXT RWD', 'category': 'vehicle', 'brand': 'Dodge', 'price_usd': 36999.99, 'discount_pct': 16.44, 'price_after_discount_usd': 30917.19, 'stock': 95}

## Q4. Where are the biggest discounts? Average discount by category, plus the single deepest cut.

Result: `q04_avg_discount_by_category.csv` (24 rows).

Top row: {'category': 'skin-care', 'products': 3, 'avg_discount_pct': 16.09, 'max_discount_pct': 18.49}

## Q5. Which products are running low on stock? Out of stock first, then the 10 lowest positive stock levels.

Result: `q05_low_stock_products.csv` (15 rows).

Top row: {'product_id': 117, 'title': 'Sportbike Motorcycle', 'category': 'motorcycle', 'brand': 'SpeedMaster', 'stock': 0, 'price_usd': 7499.99, 'availability': 'Out of Stock'}

## Q6. Which brands carry the catalogue? Products per brand and each brand's average price and rating.

Result: `q06_products_per_brand.csv` (63 rows).

Top row: {'brand': 'Apple', 'products': 14, 'avg_price_usd': 454.28, 'avg_rating': 3.55, 'total_stock': 537}

## Q7. How are product ratings distributed? Buckets: under 3, 3-4, 4-4.5, 4.5 and above.

Result: `q07_rating_distribution.csv` (4 rows).

Top row: {'rating_bucket': '3.0 - 3.9', 'products': 78, 'pct_of_catalogue': 40.2}

## Q8. Do pricier products rate better? Average rating by price band.

Result: `q08_rating_by_price_band.csv` (5 rows).

Top row: {'price_band': 'under $10', 'products': 46, 'avg_rating': 3.75, 'avg_discount_pct': 9.75}

## Q9. What are the most common tags in the catalogue?

Result: `q09_most_common_tags.csv` (15 rows).

Top row: {'tag': 'kitchen tools', 'products': 19}

## Q10. Do customer reviews agree with the listed product rating? Products where the average review rating is furthest from the rating the catalogue lists (only products with reviews).

Result: `q10_reviews_vs_listed_rating.csv` (10 rows).

Top row: {'product_id': 180, 'title': 'Dress Pea', 'listed_rating': 4.88, 'reviews': 3, 'avg_review_rating': 2.33, 'review_minus_listed': -2.55}
