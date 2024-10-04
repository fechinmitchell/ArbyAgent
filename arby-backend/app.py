import os
import requests
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env if running locally
load_dotenv()

app = Flask(__name__)

# Enable CORS
# Allow all origins for easier development and deployment
CORS(app)

# Get API key from environment variable
API_KEY = os.getenv('ODDS_API_KEY')

@app.route('/api/arbitrage', methods=['GET'])
def find_arbitrage():
    if not API_KEY:
        return jsonify({"error": "API key not found"}), 500

    url = f'https://api.the-odds-api.com/v4/sports/?apiKey={API_KEY}'
    response = requests.get(url)

    if response.status_code == 200:
        sports = response.json()
        arbs = []

        # Iterate over available sports
        for sport in sports:
            # Fetch odds for each sport
            odds_url = f'https://api.the-odds-api.com/v4/sports/{sport["key"]}/odds?regions=us,eu&apiKey={API_KEY}'
            odds_response = requests.get(odds_url)

            if odds_response.status_code == 200:
                odds_data = odds_response.json()
                for match in odds_data:
                    if len(match['bookmakers']) >= 2:
                        # Process and find arbs between different bookmakers here
                        arbs.append(match)
            else:
                print(f"Failed to fetch odds for {sport['title']}")

        return jsonify(arbs)
    else:
        return jsonify({"error": "Failed to fetch sports data"}), 500

if __name__ == '__main__':
    # Run Flask locally on port 5000
    app.run(host='0.0.0.0', port=5000)
