from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import re
import os
import glob
from textblob import TextBlob
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)

# Global variables to store data
products_df = None
reviews_df = None
tfidf_vectorizer = None
product_features_matrix = None
product_review_stats = None

def clean_text(text):
    """Clean and preprocess text data"""
    if pd.isna(text) or text == '':
        return ''
    
    # Convert to string and lowercase
    text = str(text).lower()
    
    # Remove special characters but keep letters, numbers, and spaces
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    return text

def load_and_preprocess_data():
    """Load and preprocess the Sephora dataset"""
    global products_df, reviews_df, tfidf_vectorizer, product_features_matrix, product_review_stats
    
    try:
        print("🔄 Loading Sephora dataset...")
        
        # Load product data
        if not os.path.exists('data/product_info.csv'):
            print("❌ product_info.csv not found!")
            return False
            
        products_df = pd.read_csv('data/product_info.csv')
        print(f"✅ Loaded {len(products_df)} products")
        
        # Load all review files
        review_files = glob.glob('data/reviews_*.csv')
        if not review_files:
            print("❌ No review files found!")
            return False
        
        print(f"📁 Found {len(review_files)} review files")
        
        # Combine all review files
        review_dfs = []
        for file in sorted(review_files):
            print(f"   Loading {file}...")
            df = pd.read_csv(file)
            review_dfs.append(df)
        
        reviews_df = pd.concat(review_dfs, ignore_index=True)
        print(f"✅ Combined {len(reviews_df)} total reviews")
        
        # Clean and preprocess product data
        products_df = products_df.dropna(subset=['product_name'])
        
        # Fill missing values
        products_df['brand_name'] = products_df['brand_name'].fillna('Unknown Brand')
        products_df['primary_category'] = products_df['primary_category'].fillna('Skincare')
        products_df['secondary_category'] = products_df['secondary_category'].fillna('')
        products_df['ingredients'] = products_df['ingredients'].fillna('')
        products_df['rating'] = products_df['rating'].fillna(0)
        products_df['reviews'] = products_df['reviews'].fillna(0)
        products_df['price_usd'] = products_df['price_usd'].fillna(0)
        
        # Clean text fields
        products_df['product_name_clean'] = products_df['product_name'].apply(clean_text)
        products_df['brand_name_clean'] = products_df['brand_name'].apply(clean_text)
        products_df['ingredients_clean'] = products_df['ingredients'].apply(clean_text)
        
        # Create combined features for similarity matching
        products_df['combined_features'] = (
            products_df['product_name_clean'] + ' ' +
            products_df['brand_name_clean'] + ' ' +
            products_df['primary_category'].apply(clean_text) + ' ' +
            products_df['secondary_category'].apply(clean_text) + ' ' +
            products_df['ingredients_clean']
        )
        
        # Create enhanced product stats from reviews
        print("📊 Calculating product review statistics...")
        review_stats = reviews_df.groupby('product_id').agg({
            'rating': ['mean', 'count', 'std'],
            'review_text': 'count'
        }).reset_index()
        
        # Flatten column names
        review_stats.columns = ['product_id', 'avg_rating', 'rating_count', 'rating_std', 'review_count']
        review_stats['rating_std'] = review_stats['rating_std'].fillna(0)
        
        # Merge with products
        products_df = products_df.merge(review_stats, left_on='product_id', right_on='product_id', how='left')
        
        # Use calculated stats where available, fall back to original data
        products_df['final_rating'] = products_df['avg_rating'].fillna(products_df['rating'])
        products_df['final_review_count'] = products_df['rating_count'].fillna(products_df['reviews'])
        
        # Create TF-IDF vectors for product features
        print("🧠 Creating product similarity matrix...")
        tfidf_vectorizer = TfidfVectorizer(
            max_features=8000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8
        )
        
        product_features_matrix = tfidf_vectorizer.fit_transform(products_df['combined_features'])
        
        # Create product review sentiment summary
        print("💭 Processing review sentiments...")
        sample_reviews = reviews_df.sample(min(10000, len(reviews_df)))  # Sample for performance
        
        def get_sentiment(text):
            if pd.isna(text) or text == '':
                return 0
            try:
                return TextBlob(str(text)).sentiment.polarity
            except:
                return 0
        
        sample_reviews['sentiment'] = sample_reviews['review_text'].apply(get_sentiment)
        
        product_sentiment = sample_reviews.groupby('product_id').agg({
            'sentiment': 'mean',
            'review_text': lambda x: ' '.join(str(text) for text in x.head(3))  # Sample review text
        }).reset_index()
        
        product_sentiment.columns = ['product_id', 'avg_sentiment', 'sample_reviews']
        
        products_df = products_df.merge(product_sentiment, on='product_id', how='left')
        products_df['avg_sentiment'] = products_df['avg_sentiment'].fillna(0)
        products_df['sample_reviews'] = products_df['sample_reviews'].fillna('')
        
        print("✅ Data preprocessing completed successfully!")
        print(f"📈 Final dataset: {len(products_df)} products with enhanced features")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_product_recommendations(query, skin_concerns=None, price_range=None, brand_filter=None, top_n=12):
    """Get product recommendations based on user query with filters"""
    global products_df, tfidf_vectorizer, product_features_matrix
    
    if products_df is None:
        return []
    
    # Start with all products
    filtered_products = products_df.copy()
    
    # Apply filters
    if price_range:
        min_price, max_price = price_range
        filtered_products = filtered_products[
            (filtered_products['price_usd'] >= min_price) & 
            (filtered_products['price_usd'] <= max_price)
        ]
    
    if brand_filter and brand_filter.lower() != 'all':
        filtered_products = filtered_products[
            filtered_products['brand_name'].str.lower().str.contains(brand_filter.lower(), na=False)
        ]
    
    if len(filtered_products) == 0:
        return []
    
    # Create enhanced query
    enhanced_query = clean_text(query)
    if skin_concerns:
        enhanced_query += " " + " ".join([clean_text(concern) for concern in skin_concerns])
    
    # Transform query using TF-IDF
    query_vector = tfidf_vectorizer.transform([enhanced_query])
    
    # Get indices of filtered products
    filtered_indices = filtered_products.index.tolist()
    
    # Calculate similarity only for filtered products
    filtered_features = product_features_matrix[filtered_indices]
    similarity_scores = cosine_similarity(query_vector, filtered_features).flatten()
    
    # Create results with additional scoring factors
    results = []
    for i, idx in enumerate(filtered_indices):
        if similarity_scores[i] > 0:
            product = filtered_products.loc[idx]
            
            # Calculate composite score
            base_similarity = similarity_scores[i]
            rating_bonus = (product['final_rating'] / 5.0) * 0.2  # Up to 20% bonus for high ratings
            review_bonus = min(np.log1p(product['final_review_count']) / 10, 0.1)  # Up to 10% bonus for many reviews
            sentiment_bonus = max(product['avg_sentiment'], 0) * 0.1  # Up to 10% bonus for positive sentiment
            
            composite_score = base_similarity + rating_bonus + review_bonus + sentiment_bonus
            
            results.append({
                'product_id': product['product_id'],
                'product_name': product['product_name'],
                'brand_name': product['brand_name'],
                'category': product['primary_category'],
                'subcategory': product['secondary_category'],
                'price_usd': float(product['price_usd']) if product['price_usd'] > 0 else None,
                'rating': float(product['final_rating']),
                'review_count': int(product['final_review_count']),
                'similarity_score': float(base_similarity),
                'composite_score': float(composite_score),
                'sentiment_score': float(product['avg_sentiment']),
                'ingredients': product['ingredients'][:300] + '...' if len(str(product['ingredients'])) > 300 else product['ingredients'],
                'sample_reviews': product['sample_reviews'][:200] + '...' if len(str(product['sample_reviews'])) > 200 else product['sample_reviews']
            })
    
    # Sort by composite score
    results.sort(key=lambda x: x['composite_score'], reverse=True)
    
    return results[:top_n]

def get_product_reviews(product_id, limit=5):
    """Get reviews for a specific product"""
    global reviews_df
    
    if reviews_df is None:
        return []
    
    product_reviews = reviews_df[reviews_df['product_id'] == product_id].head(limit)
    
    reviews = []
    for _, review in product_reviews.iterrows():
        reviews.append({
            'rating': int(review.get('rating', 0)),
            'review_text': str(review.get('review_text', ''))[:500],  # Limit review length
            'skin_tone': str(review.get('skin_tone', 'Not specified')),
            'eye_color': str(review.get('eye_color', 'Not specified')),
            'skin_type': str(review.get('skin_type', 'Not specified')),
            'hair_color': str(review.get('hair_color', 'Not specified')),
            'age': str(review.get('age', 'Not specified'))
        })
    
    return reviews

@app.route('/')
def home():
    return """
    <h1>🌟 Sephora Product Recommender API 🌟</h1>
    <p>Your AI-powered beauty consultant is ready!</p>
    <h3>Available Endpoints:</h3>
    <ul>
        <li><strong>POST /api/search</strong> - Search for products</li>
        <li><strong>GET /api/product/&lt;id&gt;/reviews</strong> - Get product reviews</li>
        <li><strong>GET /api/brands</strong> - Get all brands</li>
        <li><strong>GET /api/categories</strong> - Get all categories</li>
        <li><strong>GET /api/stats</strong> - Get dataset statistics</li>
    </ul>
    """

@app.route('/api/search', methods=['POST'])
def search_products():
    """Advanced product search with filters"""
    try:
        data = request.json
        query = data.get('query', '')
        skin_concerns = data.get('skin_concerns', [])
        price_range = data.get('price_range')  # [min, max]
        brand_filter = data.get('brand')
        limit = data.get('limit', 12)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        recommendations = get_product_recommendations(
            query=query,
            skin_concerns=skin_concerns,
            price_range=price_range,
            brand_filter=brand_filter,
            top_n=limit
        )
        
        return jsonify({
            'query': query,
            'filters': {
                'skin_concerns': skin_concerns,
                'price_range': price_range,
                'brand': brand_filter
            },
            'total_results': len(recommendations),
            'products': recommendations
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/product/<product_id>/reviews', methods=['GET'])
def get_reviews_endpoint(product_id):
    """Get reviews for a specific product"""
    try:
        limit = request.args.get('limit', 5, type=int)
        reviews = get_product_reviews(product_id, limit)
        
        return jsonify({
            'product_id': product_id,
            'total_reviews': len(reviews),
            'reviews': reviews
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all available product categories"""
    try:
        if products_df is None:
            return jsonify({'error': 'Data not loaded'}), 500
        
        primary_categories = products_df['primary_category'].dropna().unique().tolist()
        secondary_categories = products_df['secondary_category'].dropna().unique().tolist()
        
        return jsonify({
            'primary_categories': sorted(primary_categories),
            'secondary_categories': sorted([cat for cat in secondary_categories if cat != ''])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/brands', methods=['GET'])
def get_brands():
    """Get all available brands"""
    try:
        if products_df is None:
            return jsonify({'error': 'Data not loaded'}), 500
        
        brands = products_df['brand_name'].dropna().unique().tolist()
        brand_counts = products_df['brand_name'].value_counts().head(20).to_dict()
        
        return jsonify({
            'all_brands': sorted(brands),
            'top_brands': brand_counts
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get comprehensive dataset statistics"""
    try:
        if products_df is None or reviews_df is None:
            return jsonify({'error': 'Data not loaded'}), 500
        
        stats = {
            'dataset': {
                'total_products': len(products_df),
                'total_reviews': len(reviews_df),
                'total_brands': len(products_df['brand_name'].dropna().unique()),
                'total_categories': len(products_df['primary_category'].dropna().unique())
            },
            'ratings': {
                'average_rating': float(products_df['final_rating'].mean()),
                'median_rating': float(products_df['final_rating'].median()),
                'rating_distribution': products_df['final_rating'].value_counts().sort_index().to_dict()
            },
            'pricing': {
                'min_price': float(products_df[products_df['price_usd'] > 0]['price_usd'].min()),
                'max_price': float(products_df['price_usd'].max()),
                'average_price': float(products_df[products_df['price_usd'] > 0]['price_usd'].mean()),
                'median_price': float(products_df[products_df['price_usd'] > 0]['price_usd'].median())
            },
            'categories': products_df['primary_category'].value_counts().head(10).to_dict(),
            'top_brands': products_df['brand_name'].value_counts().head(10).to_dict()
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trending', methods=['GET'])
def get_trending():
    """Get trending products based on high ratings and review counts"""
    try:
        if products_df is None:
            return jsonify({'error': 'Data not loaded'}), 500
        
        # Calculate trending score: high rating + many reviews + positive sentiment
        trending_products = products_df[
            (products_df['final_rating'] >= 4.0) & 
            (products_df['final_review_count'] >= 50)
        ].copy()
        
        trending_products['trending_score'] = (
            trending_products['final_rating'] * 0.4 +
            np.log1p(trending_products['final_review_count']) * 0.4 +
            (trending_products['avg_sentiment'] + 1) * 2.5 * 0.2  # Normalize sentiment to 0-1 range
        )
        
        trending = trending_products.nlargest(20, 'trending_score')[
            ['product_id', 'product_name', 'brand_name', 'final_rating', 'final_review_count', 'price_usd', 'trending_score']
        ].to_dict('records')
        
        return jsonify({
            'trending_products': trending
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Sephora Product Recommender API...")
    print("=" * 50)

    # Install required packages if missing
    try:
        import textblob
    except ImportError:
        print("📦 Installing TextBlob for sentiment analysis...")
        os.system("pip install textblob")
        import textblob

    # Load and preprocess data on startup
    if load_and_preprocess_data():
        print("=" * 50)
        print("✅ Sephora API is ready!")
        print("🌐 Access the API at: http://0.0.0.0:5000")
        print("=" * 50)
        app.run(host='0.0.0.0', port=5000)
    else:
        print("❌ Failed to load data. Please check:")
        print("   - product_info.csv exists in current directory")
        print("   - reviews_*.csv files exist in current directory")
        print("   - Files are not corrupted")

