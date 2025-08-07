import requests
import difflib
import re

# Your RapidAPI key here
RAPIDAPI_KEY = "5dc4680d3cmshd2ea2e0d6d497ffp157e36jsn84d8223fadc6'"

headers = {
    "x-rapidapi-host": "real-time-sephora-api.p.rapidapi.com",
    "x-rapidapi-key": RAPIDAPI_KEY
}

def search_product(product_name):
    search_url = "https://real-time-sephora-api.p.rapidapi.com/auto-complete"
    params = {"q": product_name}

    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code != 200:
        print("Search error:", response.status_code)
        return None

    results = response.json().get("products", [])
    if not results:
        print("No products found.")
        return None

    product = results[0]
    return product["id"], product.get("display_name", "Unknown")

def fetch_product_reviews(product_id, limit=60, offset=0):
    reviews_url = "https://real-time-sephora-api.p.rapidapi.com/products-reviews"
    headers = {
        "x-rapidapi-host": "real-time-sephora-api.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    params = {
        "ProductId": product_id,
        "Limit": limit,
        "Offset": offset
    }
    response = requests.get(reviews_url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Reviews error: {response.status_code}")
        return []
    data = response.json()
    return data.get("reviews", [])


def score_review_for_needs(review, needs):
    review_lower = review.lower()
    score = 0

    for need in needs:
        need_lower = need.lower()
        if need_lower in review_lower:
            score += 2
        else:
            words = review_lower.split()
            close_matches = difflib.get_close_matches(need_lower, words, cutoff=0.8)
            if close_matches:
                score += 1
    return score

def analyze_reviews(reviews, needs):
    scored_reviews = []

    for review in reviews:
        score = score_review_for_needs(review, needs)
        scored_reviews.append((review, score))

    scored_reviews.sort(key=lambda x: -x[1])
    return scored_reviews

def get_user_input():
    product = input("What product are you interested in? ").strip()
    features = input("Describe what you want in this product (e.g. lightweight, hydrating, good for oily skin): ").strip()
    needs = [n.strip() for n in re.split(r',|;', features) if n.strip()]
    return product, needs

def main():
    print("✨ Welcome to the Beauty Product Review Analyzer ✨\n")

    product_name, needs = get_user_input()

    result = search_product(product_name)
    if result is None:
        print("No product found or an error occurred.")
        return

    product_id, product_display_name = result
    print(f"\n🔎 Found product: {product_display_name} (ID: {product_id})")
    print(f"Fetching reviews matching needs: {needs}")

    reviews = fetch_product_reviews(product_id)

    if not reviews:
        print("No reviews found for this product.")
        return

    results = analyze_reviews(reviews, needs)

    print("\n💄 Top Matching Reviews:")
    for review, score in results[:10]:  # Top 10 reviews only
        if score > 0:
            print(f"⭐️ Score: {score}\n{review}\n")
        else:
            print(f"(Low relevance): {review}\n")

if __name__ == "__main__":
    main()
