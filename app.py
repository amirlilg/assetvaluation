import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import requests
import json # Ensure json is imported for structured API responses

app = Flask(__name__)

# --- Database Configuration ---
# Use environment variable for database URL, defaulting to a local SQLite for testing
# For Docker Compose, this will be set to the PostgreSQL service URL
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///assets.db' # Default to SQLite for quick local testing without Docker
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Model ---
class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False) # e.g., 'Bitcoin', 'Gold', 'USD'
    quantity = db.Column(db.Float, nullable=False)
    buying_price_per_unit = db.Column(db.Float, nullable=False) # Price at which one unit was bought
    currency = db.Column(db.String(10), default='USD') # Base currency for calculation (all values assumed USD)

    def __repr__(self):
        return f'<Asset {self.name}: {self.quantity} @ ${self.buying_price_per_unit}>'

# --- API for fetching real-time prices ---

# Cache for prices to reduce API calls, reset on each request for simplicity in MVP
# In a real app, you'd use a more sophisticated caching mechanism (e.g., Redis, in-memory with TTL)
_price_cache = {}

def get_current_price(asset_name: str) -> float:
    """Fetches the current price for a given asset name in USD."""
    asset_name_lower = asset_name.lower()

    if asset_name_lower in _price_cache:
        return _price_cache[asset_name_lower]

    price = 0.0
    if asset_name_lower == 'bitcoin':
        try:
            # CoinGecko API for Bitcoin price
            response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd')
            response.raise_for_status()
            data = response.json()
            price = data.get('bitcoin', {}).get('usd', 0)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Bitcoin price: {e}")
            price = 0 # Fallback
    elif asset_name_lower == 'gold':
        # --- IMPORTANT MVP NOTE FOR GOLD PRICE ---
        # Real-time, free gold APIs are typically rate-limited or require keys/subscriptions.
        # For this MVP, we are using a hardcoded value.
        # In a production app, you would integrate with a reliable financial API (e.g., Nasdaq Data Link, Alpha Vantage).
        price = 2300.00 # Example: $2300 per ounce, hardcoded for MVP
    elif asset_name_lower == 'usd':
        price = 1.0 # USD is 1 USD
    else:
        # For other assets not explicitly handled, assume 1 unit is worth 1 USD
        # In a real app, you'd integrate with more extensive APIs
        price = 1.0

    _price_cache[asset_name_lower] = price
    return price

# --- API Endpoints ---

@app.route('/')
def serve_frontend():
    """Serves the main HTML page for the frontend."""
    return render_template('index.html')

@app.route('/api/assets', methods=['GET', 'POST'])
def handle_assets():
    """
    GET: Returns a list of all assets with their calculated current value,
         profit/loss, and percentage.
    POST: Adds a new asset to the database.
    """
    # Ensure database tables are created on first load/access
    with app.app_context():
        db.create_all()

    if request.method == 'GET':
        assets = Asset.query.all()
        portfolio_details = []
        total_portfolio_current_value = 0.0
        total_portfolio_buying_value = 0.0

        # Clear cache for each request to get fresh prices
        _price_cache.clear()

        for asset in assets:
            current_price_per_unit = get_current_price(asset.name)
            current_value_usd = asset.quantity * current_price_per_unit
            buying_value_usd = asset.quantity * asset.buying_price_per_unit
            
            profit_loss_usd = current_value_usd - buying_value_usd
            
            profit_loss_percentage = 0.0
            if buying_value_usd > 0:
                profit_loss_percentage = (profit_loss_usd / buying_value_usd) * 100
            elif buying_value_usd == 0 and profit_loss_usd > 0: # Bought for free and now has value
                profit_loss_percentage = float('inf') # Infinite profit
            elif buying_value_usd == 0 and profit_loss_usd < 0: # Bought for free and now has negative value (unlikely)
                profit_loss_percentage = float('-inf') # Infinite loss

            portfolio_details.append({
                'id': asset.id,
                'name': asset.name.capitalize(), # Capitalize for display
                'quantity': f"{asset.quantity:,.4f}", # Format quantity
                'buying_price_per_unit': f"${asset.buying_price_per_unit:,.2f}",
                'current_price_per_unit': f"${current_price_per_unit:,.2f}",
                'buying_value_usd': f"${buying_value_usd:,.2f}",
                'current_value_usd': f"${current_value_usd:,.2f}",
                'profit_loss_usd': f"${profit_loss_usd:,.2f}",
                'profit_loss_percentage': f"{profit_loss_percentage:,.2f}%"
            })
            total_portfolio_current_value += current_value_usd
            total_portfolio_buying_value += buying_value_usd

        overall_profit_loss_usd = total_portfolio_current_value - total_portfolio_buying_value
        overall_profit_loss_percentage = 0.0
        if total_portfolio_buying_value > 0:
            overall_profit_loss_percentage = (overall_profit_loss_usd / total_portfolio_buying_value) * 100
        elif total_portfolio_buying_value == 0 and overall_profit_loss_usd > 0:
            overall_profit_loss_percentage = float('inf')
        elif total_portfolio_buying_value == 0 and overall_profit_loss_usd < 0:
            overall_profit_loss_percentage = float('-inf')


        return jsonify({
            'assets': portfolio_details,
            'total_portfolio_current_value': f"${total_portfolio_current_value:,.2f}",
            'total_portfolio_buying_value': f"${total_portfolio_buying_value:,.2f}",
            'overall_profit_loss_usd': f"${overall_profit_loss_usd:,.2f}",
            'overall_profit_loss_percentage': f"{overall_profit_loss_percentage:,.2f}%"
        })

    elif request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        quantity = data.get('quantity')
        buying_price_per_unit = data.get('buying_price_per_unit')

        if not name or quantity is None or buying_price_per_unit is None:
            return jsonify({'error': 'Name, Quantity, and Buying Price are required.'}), 400
        
        try:
            quantity = float(quantity)
            buying_price_per_unit = float(buying_price_per_unit)
        except ValueError:
            return jsonify({'error': 'Quantity and Buying Price must be numbers.'}), 400

        # Validate positive values
        if quantity < 0 or buying_price_per_unit < 0:
             return jsonify({'error': 'Quantity and Buying Price must be non-negative.'}), 400

        new_asset = Asset(
            name=name.strip(),
            quantity=quantity,
            buying_price_per_unit=buying_price_per_unit
        )
        db.session.add(new_asset)
        db.session.commit()
        return jsonify({'message': 'Asset added successfully!', 'id': new_asset.id}), 201

@app.route('/api/assets/<int:asset_id>', methods=['DELETE'])
def delete_asset(asset_id):
    """Deletes an asset by its ID."""
    asset_to_delete = Asset.query.get(asset_id)
    if not asset_to_delete:
        return jsonify({'error': 'Asset not found.'}), 404

    db.session.delete(asset_to_delete)
    db.session.commit()
    return jsonify({'message': 'Asset deleted successfully!'}), 200

if __name__ == '__main__':
    # When running locally without Docker, ensure tables are created
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')

