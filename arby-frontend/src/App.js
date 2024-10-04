import React, { useState, useEffect } from 'react';
import './App.css';
import { Card, CardContent, Typography, CircularProgress, Container, Grid } from '@mui/material';
import './App.css';

function App() {
  const [arbitrageData, setArbitrageData] = useState([]);
  const [statusMessage, setStatusMessage] = useState('Loading...');

  // Fetching arbitrage opportunities from the backend
  useEffect(() => {
    fetch('https://arbyagent.onrender.com/api/arbitrage')
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          setStatusMessage(data.error);
        } else {
          setArbitrageData(data);
          setStatusMessage('Data loaded successfully');
        }
      })
      .catch(error => {
        console.error('Error fetching from backend:', error);
        setStatusMessage('Failed to connect to the backend.');
      });
  }, []);

  return (
    <Container className="App">
      <header className="App-header">
        <Typography variant="h2" component="h1" gutterBottom>
          Welcome to ArbyAgent!
        </Typography>
        <Typography variant="body1" gutterBottom>
          Your one-stop platform for finding arbitrage opportunities on multiple bookmakers.
        </Typography>
        <Typography variant="h5" component="h2" gutterBottom>
          Backend Connection Status:
        </Typography>
        <Typography variant="body2" color="textSecondary">
          {statusMessage}
        </Typography>

        {arbitrageData.length > 0 ? (
          <Grid container spacing={3} style={{ marginTop: '20px' }}>
            {arbitrageData.map((arb, index) => (
              <Grid item xs={12} md={6} key={index}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" component="h3">
                      {arb.sport_title}: {arb.home_team} vs {arb.away_team}
                    </Typography>
                    <Typography variant="subtitle1" component="p" style={{ marginTop: '10px' }}>
                      Bookmakers:
                    </Typography>
                    <ul>
                      {arb.bookmakers.map((bookmaker, bIndex) => (
                        <li key={bIndex}>
                          <strong>{bookmaker.title}</strong>: Odds - {bookmaker.markets[0].outcomes[0].price}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        ) : (
          <CircularProgress style={{ marginTop: '20px' }} />
        )}
      </header>
    </Container>
  );
}

export default App;
