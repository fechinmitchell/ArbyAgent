from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
import json
import logging
import time
from datetime import datetime, timedelta

# Load environment variables from .env if running locally
load_dotenv()

# Initialize Flask app and enable CORS
app = Flask(__name__, template_folder='templates')
CORS(app)

# Configure logging to output timestamp, log level, and message
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Retrieve API key from environment variables
API_KEY = os.getenv('ODDS_API_KEY')

# Log whether the API key was successfully loaded
logging.info(f"API Key Loaded: {'Yes' if API_KEY else 'No'}")

# Constants for API interaction
BASE_URL = "https://api.the-odds-api.com/v4"
DEFAULT_REGIONS = ["eu", "us", "au", "uk"]  # Default regions to get odds for

# Mapping of human-readable regions to API expected region codes
REGION_MAPPING = {
    'eu': 'eu',
    'us': 'us',
    'au': 'au',
    'uk': 'uk',
    'canada': 'ca',
    'ca': 'ca',
    'asia': 'asia',
    'africa': 'africa',
    'southamerica': 'southamerica',
    'south_america': 'southamerica',
    'latinamerica': 'latinamerica',
    'latin_america': 'latinamerica',
    'oceania': 'oceania',
    'caribbean': 'caribbean',
    'australia': 'au',  # Ensure 'australia' maps to 'au'
    'south america': 'southamerica',
    'latin america': 'latinamerica'
}

# Custom exceptions for handling API errors
class APIException(RuntimeError):
    def __init__(self, message, response=None):
        super().__init__(message)
        self.response = response

class AuthenticationException(APIException):
    pass

class RateLimitException(APIException):
    pass

# Handle faulty API responses based on status code
def handle_faulty_response(response: requests.Response):
    if response.status_code == 401:
        raise AuthenticationException("Failed to authenticate with the API. Is the API key valid?", response)
    elif response.status_code == 429:
        raise RateLimitException("Encountered API rate limit.", response)
    else:
        try:
            error_message = response.json().get('message', 'No message provided')
        except json.JSONDecodeError:
            error_message = "No message provided"
        raise APIException(f"Unknown issue: {error_message}", response)

# Fetch available sports from The Odds API
def get_sports(key: str) -> set:
    url = f"{BASE_URL}/sports/"
    params = {"apiKey": key}

    response = requests.get(url, params=params)
    if response.status_code != 200:
        handle_faulty_response(response)

    try:
        sports = response.json()
    except json.JSONDecodeError:
        logging.error("Invalid JSON response when fetching sports.")
        raise APIException("Invalid JSON response when fetching sports.", response)

    # Extract sport keys from the response
    sport_keys = {item["key"] for item in sports}
    logging.info(f"Fetched {len(sport_keys)} sports.")
    return sport_keys

# Fetch odds data for a given sport and regions
def get_data(key: str, sport: str, regions: list):
    url = f"{BASE_URL}/sports/{sport}/odds/"
    params = {
        "apiKey": key,
        "regions": ",".join(regions),
        "markets": "h2h",  # Only get head-to-head markets
        "oddsFormat": "decimal",
        "dateFormat": "unix"
    }

    logging.info(f"Fetching data for sport: {sport} with regions: {regions}")
    response = requests.get(url, params=params)
    if response.status_code != 200:
        handle_faulty_response(response)

    try:
        data = response.json()
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON response for sport: {sport}.")
        raise APIException(f"Invalid JSON response for sport: {sport}.", response)

    return data

# Process match data to find arbitrage opportunities
def process_data(matches: list, include_started_matches: bool = True, selected_bookmakers: list = None) -> list:
    arbs = []
    current_time = time.time()

    for match in matches:
        start_time = match.get("commence_time", 0)
        is_live = start_time <= current_time and start_time != 0

        # Skip matches that have already started if not including them
        if not include_started_matches and start_time < current_time:
            logging.debug(f"Skipping already started match: {match.get('home_team')} vs {match.get('away_team')}")
            continue

        bookmakers = match.get("bookmakers", [])

        # Skip if there are not enough bookmakers to create an arbitrage
        if len(bookmakers) < 2:
            logging.debug(f"Skipping {match.get('home_team')} vs {match.get('away_team')} due to insufficient bookmakers.")
            continue

        # Extract match information
        event = f"{match.get('home_team', 'Unknown')} vs. {match.get('away_team', 'Unknown')}"
        sport_key = match.get('sport_key', 'Unknown')
        match_date = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S') if start_time else 'N/A'

        # Determine available outcomes dynamically
        outcomes_set = set()
        for bookmaker in bookmakers:
            for market in bookmaker.get('markets', []):
                if market.get('key') != 'h2h':
                    continue
                for outcome in market.get('outcomes', []):
                    name = outcome.get('name')
                    if name:
                        outcomes_set.add(name.strip())

        if len(outcomes_set) < 2:
            logging.debug(f"Skipping {event} due to insufficient outcomes.")
            continue

        required_outcomes = list(outcomes_set)
        logging.debug(f"Processing event: {event}")
        logging.debug(f"Required outcomes: {required_outcomes}")

        # Find the best odds for each outcome
        best_odds = {}
        for bookmaker in bookmakers:
            # Filter bookmakers based on user selection
            if selected_bookmakers and bookmaker.get('title') not in selected_bookmakers:
                continue

            for market in bookmaker.get('markets', []):
                if market.get('key') != 'h2h':
                    continue  # Only consider head-to-head markets
                for outcome in market.get('outcomes', []):
                    team_name = outcome.get('name')
                    price = outcome.get('price')
                    if not team_name or not price:
                        continue

                    # Standardize team name and update best odds if higher
                    standardized_name = team_name.strip()
                    if standardized_name not in best_odds or best_odds[standardized_name]['price'] < price:
                        best_odds[standardized_name] = {
                            'price': price,
                            'bookmaker': bookmaker.get('title', 'Unknown Bookmaker'),
                            'link': bookmaker.get('link', f"https://www.example.com/{sport_key}/{event.replace(' ', '-')}?bookmaker={bookmaker.get('title', 'Unknown Bookmaker')}")
                        }

        logging.debug(f"Best odds for event {event}: {best_odds}")

        # Ensure all required outcomes are present in best_odds
        if not all(outcome in best_odds for outcome in required_outcomes):
            logging.debug(f"Skipping {event} due to missing required outcomes in best_odds.")
            continue

        # Calculate implied probability of each outcome
        try:
            implied_probability = sum(1 / best_odds[outcome]['price'] for outcome in required_outcomes)
            logging.debug(f"Implied probability for {event}: {implied_probability:.4f}")
        except ZeroDivisionError:
            logging.warning(f"Invalid price encountered for {event}. Skipping.")
            continue

        # Check if there's an arbitrage opportunity (implied probability < 1)
        threshold = 1.0
        epsilon = 1e-5  # Small value to account for floating-point precision
        if implied_probability < (threshold - epsilon):
            profit = round((threshold - implied_probability) * 100, 2)
            # Structure odds as a list for frontend compatibility
            odds_list = [
                {
                    'team': outcome,
                    'price': best_odds[outcome]['price'],
                    'bookmaker': best_odds[outcome]['bookmaker'],
                    'stake': round((1 / best_odds[outcome]['price']) / implied_probability * 100, 2),  # Calculate stake percentage
                    'link': best_odds[outcome]['link']  # Include link for placing bet
                }
                for outcome in required_outcomes
            ]
            arb = {
                'sport': sport_key,
                'event': event,
                'date': match_date,
                'profit': profit,
                'is_live': is_live,  # Add live status
                'odds': odds_list
            }
            arbs.append(arb)
            logging.info(f"Arb found for {event}: Profit {profit}%")
        else:
            logging.debug(f"No arbitrage opportunity for {event}. Implied probability: {implied_probability:.4f}")

    # Sort arbitrage opportunities by profit in descending order
    arbs.sort(key=lambda x: x['profit'], reverse=True)
    logging.info(f"Total arbs found: {len(arbs)}")

    return arbs

# Retrieve arbitrage opportunities across all sports
def get_arbitrage_opportunities(key: str, regions: list, selected_bookmakers: list, cutoff: float, timeframe: str):
    try:
        # Map human-readable regions to API expected region codes
        mapped_regions = []
        for region in regions:
            mapped = REGION_MAPPING.get(region.lower())
            if mapped:
                mapped_regions.append(mapped)
            else:
                logging.warning(f"Region '{region}' is invalid and will be skipped.")

        if not mapped_regions:
            logging.error("No valid regions provided after mapping.")
            return [], []

        # Fetch available sports
        sports = get_sports(key)
    except APIException as e:
        logging.error(f"Error fetching sports: {e}")
        return [], []

    all_arbs = []
    current_time = datetime.now()

    # Determine the date range for filtering
    if timeframe == 'today':
        start_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = current_time.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif timeframe == 'week':
        start_time = current_time - timedelta(days=current_time.weekday())
        end_time = start_time + timedelta(days=6)
    elif timeframe == 'month':
        start_time = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_time = (start_time + timedelta(days=31)).replace(day=1) - timedelta(seconds=1)
    else:
        start_time = None
        end_time = None

    # Initialize a list to hold all fetched matches
    all_fetched_matches = []

    for sport in sports:
        logging.info(f"Fetching odds for sport: {sport}")
        try:
            # Fetch match data for each sport
            matches = get_data(key, sport, mapped_regions)
        except APIException as e:
            logging.error(f"Error fetching odds for sport {sport}: {e}")
            continue

        # Filter matches based on the selected timeframe
        if start_time and end_time:
            matches = [match for match in matches if start_time.timestamp() <= match.get("commence_time", 0) <= end_time.timestamp()]

        logging.info(f"Processing {len(matches)} matches for sport: {sport}")

        # Append fetched matches to the master list
        all_fetched_matches.extend(matches)

    # Process all fetched matches to find arbitrage opportunities
    arbs = process_data(all_fetched_matches, include_started_matches=False, selected_bookmakers=selected_bookmakers)
    # Filter arbitrage opportunities based on profit cutoff
    filtered_arbs = [arb for arb in arbs if arb['profit'] >= cutoff]
    all_arbs.extend(filtered_arbs)

    # Sort arbitrage opportunities by the match date in ascending order
    all_arbs.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d %H:%M:%S'))

    return all_arbs, all_fetched_matches

# Define the directory to store data dumps
DATA_DUMPS_DIR = os.path.join(os.path.dirname(__file__), 'data_dumps')

# Create the directory if it doesn't exist
if not os.path.exists(DATA_DUMPS_DIR):
    os.makedirs(DATA_DUMPS_DIR)
    logging.info(f"Created data dumps directory at {DATA_DUMPS_DIR}")

# API endpoint to list all data dump files
@app.route('/api/list_data_dumps', methods=['GET'])
def list_data_dumps():
    try:
        files = os.listdir(DATA_DUMPS_DIR)
        json_files = [file for file in files if file.endswith('.json')]
        # Sort files by modification time descending
        json_files.sort(key=lambda x: os.path.getmtime(os.path.join(DATA_DUMPS_DIR, x)), reverse=True)
        return jsonify({"data_dumps": json_files})
    except Exception as e:
        logging.error(f"Error listing data dumps: {e}")
        return jsonify({"error": "Failed to list data dumps."}), 500

# API endpoint to retrieve arbitrage opportunities from live API data
@app.route('/api/arbitrage', methods=['GET'])
def get_arbitrage():
    if not API_KEY:
        logging.error("API key not found in environment variables.")
        return jsonify({"error": "API key not found."}), 500

    timeframe = request.args.get('timeframe', 'today')
    regions = request.args.getlist('regions')  # Get regions from query parameters
    selected_bookmakers = request.args.getlist('bookmakers')  # Get selected bookmakers from query parameters

    logging.info(f"Received request for live arbitrage with timeframe={timeframe}, regions={regions}, bookmakers={selected_bookmakers}")

    try:
        # Retrieve arbitrage opportunities and all fetched matches
        arbitrage_opportunities, fetched_matches = get_arbitrage_opportunities(
            key=API_KEY,
            regions=regions if regions else DEFAULT_REGIONS,
            selected_bookmakers=selected_bookmakers,
            cutoff=0,  # Set minimum profit margin (0 means no cutoff)
            timeframe=timeframe
        )
    except Exception as e:
        logging.exception("An unexpected error occurred while fetching arbs.")
        return jsonify({"error": "An unexpected error occurred."}), 500

    if arbitrage_opportunities:
        logging.info(f"Total arbitrage opportunities found: {len(arbitrage_opportunities)}")
    else:
        logging.info("No arbitrage opportunities found.")

    # Save all fetched matches to a single data dump file with timestamp
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"data_dump_{timestamp}.json"
        file_path = os.path.join(DATA_DUMPS_DIR, filename)
        with open(file_path, 'w') as f:
            json.dump(fetched_matches, f, indent=2)
        logging.info(f"Saved all fetched data to {file_path}")
    except Exception as e:
        logging.error(f"Failed to save fetched data to file: {e}")

    # Also save the arbitrage opportunities to a separate file if desired
    try:
        arb_filename = f"arbitrage_data_dump_{timestamp}.json"
        arb_file_path = os.path.join(DATA_DUMPS_DIR, arb_filename)
        with open(arb_file_path, 'w') as f:
            json.dump(arbitrage_opportunities, f, indent=2)
        logging.info(f"Saved arbitrage data to {arb_file_path}")
    except Exception as e:
        logging.error(f"Failed to save arbitrage data to file: {e}")

    return jsonify({"arbs": arbitrage_opportunities})

# API endpoint to retrieve arbitrage opportunities from local file data
@app.route('/api/local_arbitrage', methods=['GET'])
def get_local_arbitrage():
    # Extract query parameters to allow frontend to specify filters
    timeframe = request.args.get('timeframe', 'today')
    regions = request.args.getlist('regions')  # Get regions from query parameters
    selected_bookmakers = request.args.getlist('bookmakers')  # Get selected bookmakers from query parameters
    filename = request.args.get('filename')  # Get the specific filename to use

    if not filename:
        logging.error("No filename provided for local arbitrage.")
        return jsonify({'error': 'No filename provided.'}), 400

    # Ensure the filename is secure and exists
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(DATA_DUMPS_DIR, safe_filename)

    if not os.path.exists(file_path):
        logging.error(f"Data dump file not found: {file_path}")
        return jsonify({'error': 'Data dump file not found.'}), 404

    logging.info(f"Received request for local arbitrage with timeframe={timeframe}, regions={regions}, bookmakers={selected_bookmakers}, filename={filename}")

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        if not isinstance(data, list):
            logging.error("Data dump does not contain a list of matches.")
            raise ValueError("Invalid data format in data dump.")

        logging.info(f"Loaded {len(data)} matches from {filename}")

        # Retrieve arbitrage opportunities from local data
        arbitrage_opportunities = process_data(
            matches=data,
            include_started_matches=False,
            selected_bookmakers=selected_bookmakers
        )

        logging.info(f"Found {len(arbitrage_opportunities)} arbitrage opportunities in local data")

        # Apply timeframe filtering similar to live data
        current_time = datetime.now()

        if timeframe == 'today':
            start_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = current_time.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif timeframe == 'week':
            start_time = current_time - timedelta(days=current_time.weekday())
            end_time = start_time + timedelta(days=6)
        elif timeframe == 'month':
            start_time = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_time = (start_time + timedelta(days=31)).replace(day=1) - timedelta(seconds=1)
        else:
            start_time = None
            end_time = None

        if start_time and end_time:
            arbitrage_opportunities = [
                arb for arb in arbitrage_opportunities
                if start_time <= datetime.strptime(arb['date'], '%Y-%m-%d %H:%M:%S') <= end_time
            ]
            logging.info(f"After timeframe filtering: {len(arbitrage_opportunities)} arbitrage opportunities")

        # Sort arbitrage opportunities by profit in descending order
        arbitrage_opportunities.sort(key=lambda x: x['profit'], reverse=True)

    except FileNotFoundError:
        logging.error("Data dump file not found.")
        return jsonify({'error': 'Data dump file not found.'}), 500
    except json.JSONDecodeError:
        logging.error("Invalid JSON format in data dump.")
        return jsonify({'error': 'Invalid JSON format in data dump.'}), 500
    except Exception as e:
        logging.error(f"Error reading or processing local data: {e}")
        return jsonify({'error': 'Failed to read or process local data'}), 500

    return jsonify({"arbs": arbitrage_opportunities})

# API endpoint to retrieve available bookmakers for given regions
@app.route('/api/bookmakers', methods=['GET'])
def get_bookmakers():
    regions = request.args.getlist('regions')  # Use getlist to get multiple regions
    regions = [region.lower() for region in regions]

    bookmakers_for_regions = {
        'us': ['BetMGM', 'FanDuel', 'DraftKings'],
        'ca': ['Bovada', 'BetUS'],
        'eu': [
            '888sport', 'Betclic', '1xBet', 'Paddy Power', 'FanDuel', 'Suprabets',
            'Marathon Bet', 'Betway', 'Betsson', 'Nordic Bet', 'Coral', 'Ladbrokes',
            'Neds', 'Coolbet', 'Pinnacle', 'Bet Victor', 'Betfair', 'Tipico',
            'William Hill', 'Unibet', 'Casumo', 'LeoVegas', 'Virgin Bet',
            'LiveScore Bet', 'Grosvenor', 'LowVig.ag', 'Mr Green', 'LiveScore Bet (EU)'
        ],
        'au': ['SportsBet', 'PointsBet (AU)', 'Neds', 'PlayUp', 'TAB', 'TABtouch', 'Betr'],
    }

    # Map regions using REGION_MAPPING
    mapped_regions = []
    for region in regions:
        mapped = REGION_MAPPING.get(region)
        if mapped:
            mapped_regions.append(mapped)
        else:
            logging.warning(f"Region '{region}' is not recognized and will be skipped.")

    # Collect bookmakers based on mapped regions
    selected_bookmakers = set()
    for region in mapped_regions:
        if region in bookmakers_for_regions:
            selected_bookmakers.update(bookmakers_for_regions[region])
        else:
            logging.warning(f"Region '{region}' is not recognized and will be skipped.")

    logging.info(f"Retrieved bookmakers for regions {mapped_regions}: {selected_bookmakers}")

    return jsonify({"bookmakers": list(selected_bookmakers)})

# Web interface to display arbitrage opportunities
@app.route('/')
def index():
    return render_template('index.html')

# Run the Flask app on host 0.0.0.0 and port  
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)