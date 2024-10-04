from flask import Flask, jsonify
from flask_cors import CORS

# Initialize the Flask application
app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

@app.route('/api/odds', methods=['GET'])
def get_odds():
    # Placeholder response for the odds API
    return jsonify({"message": "Arbitrage opportunities will be returned here."})

# Ensure that the app runs only if the script is executed directly
if __name__ == '__main__':
    # Only use this for local development. Use gunicorn for production.
    app.run(host='0.0.0.0', port=5000)
