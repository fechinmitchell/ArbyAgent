import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [backendMessage, setBackendMessage] = useState('Loading...');

  // Fetching data from the backend
  useEffect(() => {
    fetch('https://arbyagent.onrender.com/api/odds')
      .then(response => response.json())
      .then(data => setBackendMessage(data.message))
      .catch(error => {
        console.error('Error fetching from backend:', error);
        setBackendMessage('Failed to connect to the backend.');
      });
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Welcome to ArbyAgent!</h1>
        <p>Your one-stop platform for automated arbitrage betting.</p>
        <p>
          This website is designed to connect with multiple bookmakers and fetch
          real-time odds, allowing you to find arbitrage opportunities and make
          risk-free bets. The goal is to streamline the betting process and help
          you maximize your profits with minimal effort.
        </p>
        <h2>Backend Connection Status:</h2>
        <p>{backendMessage}</p>
      </header>
    </div>
  );
}

export default App;
