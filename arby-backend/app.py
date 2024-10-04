from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/odds', methods=['GET'])
def get_odds():
    # Placeholder response
    return jsonify({"message": "Arbitrage opportunities will be returned here."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)