from flask import Flask, request, jsonify
from flask_cors import CORS
import difflib

app = Flask(__name__)
CORS(app)  # Allow requests from your React frontend

# ---------- Cleaned product data ----------
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
        "Covers everything without feeling too heavy.",
        "Long-wearing formula perfect for events.",
        "Can be tricky to blend quickly.",
        "Not ideal for no-makeup look."
    ],
    "Sheer Foundation": [
        "Very natural skin-like finish.",
        "Light coverage that evens tone.",
        "Dewy finish that looks fresh.",
        "Best for normal to dry skin.",
        "May not control oil well."
    ]
}

# ---------- Review scoring function ----------
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

# ---------- Routes ----------
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # <-- Enable CORS for all domains and routes

@app.route('/api/recommend', methods=['POST'])
def recommend():
    data = request.json
    product = data.get('product')
    features = data.get('features')
    # Process data and create recommendations list
    recommendations = ["Example product 1", "Example product 2"]  # your logic here

    return jsonify({"recommendations": recommendations})

def search_reviews():
    """
    Accept JSON body:
    {
      "product": "Matte Concealer",
      "needs": ["good for oily skin", "long lasting"]
    }
    Returns the top reviews matching needs with scores.
    """
    data = request.get_json()
    product = data.get('product', '')
    needs = data.get('needs', [])
    
    if product not in PRODUCTS:
        return jsonify({"error": "Product not found"}), 404
    if not needs:
        return jsonify({"error": "Needs list is empty"}), 400
    
    reviews = PRODUCTS[product]
    
    scored_reviews = []
    for review in reviews:
        score = score_review_for_needs(review, needs)
        scored_reviews.append({"review": review, "score": score})
    
    # Sort descending by score
    scored_reviews.sort(key=lambda x: x['score'], reverse=True)
    
    return jsonify({
        "product": product,
        "top_reviews": scored_reviews
    })

# ---------- Main ----------
if __name__ == '__main__':
    app.run(debug=True, port=5500)
