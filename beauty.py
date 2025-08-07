import difflib
import re
import sys

# Expanded offline database of products and reviews
PRODUCTS = {
    "Matte Concealer": [
        "Very matte finish, great for oily skin.",
        "Doesn't crease but can feel drying.",
        "Long-lasting and covers blemishes well.",
        "Not hydrating enough for dry under eyes."
    ],
    "Blurring Powder": [
        "Smooths pores and gives an airbrushed finish.",
        "Feels lightweight and keeps shine away.",
        "Can look cakey if over-applied.",
        "Excellent for setting concealer."
    ],
    "Brightening Powder": [
        "Brightens under eyes beautifully.",
        "Lightweight and doesn't settle into lines.",
        "Adds a soft radiance without glitter.",
        "Can emphasize texture if skin is dry."
    ],
    "Full Coverage Concealer": [
        "Incredible coverage for dark circles.",
        "Thick formula but blends well.",
        "Can look heavy if too much is used.",
        "Lasts all day without fading."
    ],
    "Dewy Blush": [
        "Gives a fresh, natural glow.",
        "Blends easily and feels hydrating.",
        "Can be too shiny for oily skin.",
        "Beautiful color payoff."
    ],
    "Matte Blush": [
        "Very pigmented and stays matte all day.",
        "Blends well without patchiness.",
        "Great for controlling shine.",
        "Not ideal for dry skin."
    ],
    "Satin Blush": [
        "Natural finish with a slight glow.",
        "Easy to blend and build.",
        "Looks flattering on mature skin.",
        "Not overly shiny."
    ],
    "Liquid Blush": [
        "Blends seamlessly into the skin.",
        "Lightweight and buildable color.",
        "Can be tricky to apply over powder.",
        "Very natural-looking finish."
    ],
    "Powder Blush": [
        "Classic formula, easy to use.",
        "Good color payoff and longevity.",
        "Can look powdery on dry skin.",
        "Affordable and reliable."
    ],
    "Liquid Bronzer": [
        "Blends like a dream for a natural bronze.",
        "Lightweight and easy to layer.",
        "Can look too warm on fair skin.",
        "Gives a dewy finish."
    ],
    "Powder Bronzer": [
        "Matte finish perfect for oily skin.",
        "Blends easily without looking muddy.",
        "Wide shade range.",
        "Lasts all day without fading."
    ],
    "Matte Foundation": [
        "Controls shine all day.",
        "Excellent for oily skin types.",
        "Can emphasize dry patches.",
        "Great coverage and lasting power."
    ],
    "Full Coverage Foundation": [
        "Covers everything without feeling too heavy.",
        "Long-wearing formula perfect for events.",
        "Can be tricky to blend quickly.",
        "Not ideal for no-makeup look."
    ],
    "Sheer Foundation": [
        "Very natural skin-like finish.",
        "Light coverage that evens tone.",
        "Great for everyday use.",
        "Won't cover major blemishes."
    ],
    "Skin Tint": [
        "Feels like nothing on the skin.",
        "Very light coverage, perfect for good skin days.",
        "Gives a healthy glow.",
        "Not long-lasting without powder."
    ],
    "Foundation with SPF": [
        "Lightweight with built-in sun protection.",
        "Great for daily wear outdoors.",
        "May flash back in photos.",
        "Good for minimal makeup days."
    ],
    "Foundation with No Pore Cloggers": [
        "Non-comedogenic, doesn't break me out.",
        "Lightweight and breathable formula.",
        "Great for acne-prone skin.",
        "Still offers decent coverage."
    ]
}


def list_products():
    print("\n🛍️ Available products:")
    for i, name in enumerate(PRODUCTS.keys(), 1):
        print(f"{i}. {name}")
    print()


def get_user_product_choice():
    list_products()
    choice = input("💬 Enter the number of the product you're interested in: ").strip()
    if not choice.isdigit():
        print("❌ Invalid input. Must be a number.")
        sys.exit(1)
    choice = int(choice)
    if choice < 1 or choice > len(PRODUCTS):
        print("❌ Invalid choice number.")
        sys.exit(1)
    product_name = list(PRODUCTS.keys())[choice - 1]
    return product_name


def get_user_needs():
    features = input(
        "💬 Describe what you want in this product (e.g. lightweight, hydrating, good for oily skin): "
    ).strip()
    if not features:
        print("❌ Feature list cannot be empty.")
        sys.exit(1)
    needs = [n.strip() for n in re.split(r',|;', features) if n.strip()]
    return needs


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


def main():
    print("✨ Welcome to the Offline Beauty Product Review Analyzer ✨\n")
    product_name = get_user_product_choice()
    needs = get_user_needs()

    print(f"\n✅ Selected product: {product_name}")
    print(f"🧪 Analyzing reviews for needs: {needs}")

    reviews = PRODUCTS[product_name]
    results = analyze_reviews(reviews, needs)

    print(f"\n✅ Product: {product_name}")
    print("\n💄 Top Matching Reviews:")

    any_high_score = False
    top_reviews = []
    for review, score in results:
        if score > 0:
            any_high_score = True
            print(f"\n⭐️ Score: {score}\n{review}\n{'-'*40}")
            top_reviews.append((review, score))

    if not any_high_score:
        print("⚠️ No reviews matched your criteria very well. Try broader keywords!")

    return product_name, top_reviews

if __name__ == "__main__":
    main()
