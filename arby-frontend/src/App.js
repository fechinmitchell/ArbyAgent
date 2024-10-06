import React, { useState, useEffect, useMemo } from 'react';
import './App.css';
import {
  Container,
  Typography,
  Button,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Link,
  Chip,
  Checkbox,
  FormGroup,
  FormControlLabel,
  Alert,
  Box,
  Stack, // Import Stack
} from '@mui/material';
import { styled } from '@mui/system';

// Custom style for FormControl to match button size
const StyledFormControl = styled(FormControl)({
  minWidth: 200,
  '& .MuiInputLabel-root': {
    color: '#61dafb', // Label color
  },
  '& .MuiSelect-outlined': {
    backgroundColor: 'white',
    color: '#282c34',
  },
  '& .MuiOutlinedInput-root': {
    '& fieldset': {
      borderColor: '#61dafb',
    },
    '&:hover fieldset': {
      borderColor: '#FF8E53',
    },
    '&.Mui-focused fieldset': {
      borderColor: '#FE6B8B',
    },
  },
});

function App() {
  const [arbitrageData, setArbitrageData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [timeframe, setTimeframe] = useState('week'); // Set to 'week' by default
  const [betAmount, setBetAmount] = useState('');
  const [selectedRegions, setSelectedRegions] = useState(['EU']); // Select 'EU' by default for testing
  const [availableBookmakers, setAvailableBookmakers] = useState([]);
  const [selectedBookmakers, setSelectedBookmakers] = useState([]);
  const [error, setError] = useState(null);
  const [availableDataDumps, setAvailableDataDumps] = useState([]);
  const [selectedDataDump, setSelectedDataDump] = useState('');

  const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:5000';

  // Regions available for betting
  const regions = ['Canada', 'EU', 'US', 'Australia'];

  // Fetch available bookmakers whenever selectedRegions changes
  useEffect(() => {
    if (selectedRegions.length === 0) {
      setAvailableBookmakers([]);
      setSelectedBookmakers([]);
      return;
    }

    const fetchBookmakers = async () => {
      try {
        const params = new URLSearchParams();
        selectedRegions.forEach((region) => params.append('regions', region.toLowerCase()));
        const response = await fetch(`${backendUrl}/api/bookmakers?${params.toString()}`);
        if (!response.ok) {
          throw new Error('Failed to fetch bookmakers.');
        }
        const data = await response.json();
        setAvailableBookmakers(data.bookmakers);
        // Reset selectedBookmakers if they are no longer available
        setSelectedBookmakers((prevSelected) =>
          prevSelected.filter((bookmaker) => data.bookmakers.includes(bookmaker))
        );
      } catch (err) {
        console.error('Error fetching bookmakers:', err);
        setError('Failed to fetch bookmakers. Please try again later.');
      }
    };

    fetchBookmakers();
  }, [selectedRegions, backendUrl]);

  // Initialize selectedBookmakers after bookmakers are fetched
  useEffect(() => {
    if (availableBookmakers.length > 0 && selectedBookmakers.length === 0) {
      setSelectedBookmakers([...availableBookmakers]); // Select all by default for testing
    }
  }, [availableBookmakers, selectedBookmakers.length]);

  // Fetch available data dumps on component mount
  useEffect(() => {
    const fetchDataDumps = async () => {
      try {
        const response = await fetch(`${backendUrl}/api/list_data_dumps`);
        if (!response.ok) {
          throw new Error('Failed to fetch data dumps.');
        }
        const data = await response.json();
        setAvailableDataDumps(data.data_dumps);
      } catch (err) {
        console.error('Error fetching data dumps:', err);
        setError('Failed to fetch data dumps.');
      }
    };

    fetchDataDumps();
  }, [backendUrl]);

  const handleRegionChange = (region) => {
    setSelectedRegions((prevRegions) => {
      const updatedRegions = prevRegions.includes(region)
        ? prevRegions.filter((r) => r !== region)
        : [...prevRegions, region];
      return updatedRegions;
    });
  };

  const handleBookmakerChange = (bookmaker) => {
    setSelectedBookmakers((prevBookmakers) =>
      prevBookmakers.includes(bookmaker)
        ? prevBookmakers.filter((b) => b !== bookmaker)
        : [...prevBookmakers, bookmaker]
    );
  };

  const handleSelectAllBookmakers = () => {
    if (selectedBookmakers.length === availableBookmakers.length) {
      setSelectedBookmakers([]);
    } else {
      setSelectedBookmakers([...availableBookmakers]);
    }
  };

  const handleDataDumpChange = (event) => {
    setSelectedDataDump(event.target.value);
  };

  // Fetch arbitrage data from the live API
  const fetchArbitrageData = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append('timeframe', timeframe);
      selectedRegions.forEach((region) => params.append('regions', region.toLowerCase()));
      selectedBookmakers.forEach((bookmaker) => params.append('bookmakers', bookmaker));

      const response = await fetch(`${backendUrl}/api/arbitrage?${params.toString()}`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to fetch arbitrage data.');
      }

      const data = await response.json();
      if (data && data.arbs) {
        setArbitrageData(data.arbs);
        // Refresh data dumps after fetching new data
        fetchDataDumps();
      } else {
        setArbitrageData([]);
      }
    } catch (err) {
      console.error('Error fetching from backend:', err);
      setError(err.message || 'Failed to fetch arbitrage data.');
    } finally {
      setLoading(false);
    }
  };

  // Fetch arbitrage data from the local file (via the backend)
  const fetchArbitrageDataFromFile = async () => {
    if (!selectedDataDump) {
      setError('Please select a data dump file.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append('timeframe', timeframe);
      selectedRegions.forEach((region) => params.append('regions', region.toLowerCase()));
      selectedBookmakers.forEach((bookmaker) => params.append('bookmakers', bookmaker));
      params.append('filename', selectedDataDump); // Include the selected filename

      const response = await fetch(`${backendUrl}/api/local_arbitrage?${params.toString()}`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to fetch local arbitrage data.');
      }

      const data = await response.json();
      if (data && data.arbs) {
        setArbitrageData(data.arbs);
      } else {
        setArbitrageData([]);
      }
    } catch (err) {
      console.error('Error fetching from local file:', err);
      setError(err.message || 'Failed to fetch local arbitrage data.');
    } finally {
      setLoading(false);
    }
  };

  // Calculate actual stake amounts and expected return based on betAmount
  const processedArbitrageData = useMemo(() => {
    if (!betAmount || isNaN(betAmount) || parseFloat(betAmount) <= 0) {
      return arbitrageData.map((arb) => ({ ...arb, expectedReturn: 'N/A' }));
    }

    const totalStake = parseFloat(betAmount);

    return arbitrageData.map((arb) => {
      // Calculate expected return
      const expectedReturn =
        arb.profit > 0
          ? (totalStake / (1 - arb.profit / 100)).toFixed(2)
          : 'N/A';

      // Calculate stake amounts based on stake percentages
      const stakes = arb.odds.map((oddsInfo) => ({
        ...oddsInfo,
        stakeAmount: arb.profit > 0
          ? ((oddsInfo.stake / 100) * totalStake).toFixed(2)
          : '0.00',
      }));

      return { ...arb, odds: stakes, expectedReturn };
    });
  }, [arbitrageData, betAmount]);

  // Function to refresh data dumps after fetching new data
  const fetchDataDumps = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/list_data_dumps`);
      if (!response.ok) {
        throw new Error('Failed to fetch data dumps.');
      }
      const data = await response.json();
      setAvailableDataDumps(data.data_dumps);
    } catch (err) {
      console.error('Error fetching data dumps:', err);
      setError('Failed to fetch data dumps.');
    }
  };

  return (
    <Container maxWidth="lg" className="App">
      <header className="App-header">
        <Typography variant="h3" component="h1" gutterBottom>
          Welcome to ArbyAgent!
        </Typography>
        <Typography variant="h6" component="p" gutterBottom>
          Your one-stop platform for finding arbitrage opportunities on multiple bookmakers.
        </Typography>

        {/* Main Stack for Inputs and Buttons */}
        <Stack spacing={3} width="100%" marginTop={2} marginBottom={2} alignItems="center">
          {/* Inputs Stack */}
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={2}
            alignItems={{ xs: 'stretch', sm: 'center' }}
            width="100%"
            maxWidth="800px"
          >
            <StyledFormControl variant="outlined">
              <InputLabel>Timeframe</InputLabel>
              <Select
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
                label="Timeframe"
              >
                <MenuItem value="today">Today</MenuItem>
                <MenuItem value="week">This Week</MenuItem>
                <MenuItem value="month">This Month</MenuItem>
              </Select>
            </StyledFormControl>

            <FormControl variant="outlined" style={{ minWidth: 200 }}>
              <InputLabel>Data Dump</InputLabel>
              <Select
                value={selectedDataDump}
                onChange={handleDataDumpChange}
                label="Data Dump"
              >
                <MenuItem value="">
                  <em>None</em>
                </MenuItem>
                {availableDataDumps.map((dump) => (
                  <MenuItem value={dump} key={dump}>
                    {dump}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="Bet Amount ($)"
              variant="outlined"
              value={betAmount}
              onChange={(e) => setBetAmount(e.target.value)}
              type="number"
              InputProps={{ inputProps: { min: 0 } }}
              style={{ minWidth: '150px' }}
            />
          </Stack>

          {/* Buttons Stack */}
          <Stack
            direction="column"
            spacing={2}
            alignItems="center"
            width="100%"
            maxWidth="300px"
          >
            <Button
              variant="contained"
              color="primary"
              onClick={fetchArbitrageData}
              disabled={loading || selectedRegions.length === 0 || selectedBookmakers.length === 0}
              style={{ width: '100%' }}
              className="check-button"
            >
              {loading ? <CircularProgress size={24} color="inherit" /> : 'Check Arbitrage Opportunities'}
            </Button>
            <Button
              variant="contained"
              color="secondary"
              onClick={fetchArbitrageDataFromFile}
              disabled={
                loading ||
                selectedRegions.length === 0 ||
                selectedBookmakers.length === 0 ||
                !selectedDataDump
              }
              style={{ width: '100%' }}
              className="test-button"
            >
              {loading ? <CircularProgress size={24} color="inherit" /> : 'Test with Local Data'}
            </Button>
          </Stack>
        </Stack>

        {/* Display error message if any */}
        {error && (
          <Alert severity="error" onClose={() => setError(null)} style={{ marginBottom: '20px' }}>
            {error}
          </Alert>
        )}

        {/* Region Selection */}
        <FormGroup row style={{ marginBottom: '20px' }}>
          {regions.map((region) => (
            <FormControlLabel
              control={
                <Checkbox
                  checked={selectedRegions.includes(region)}
                  onChange={() => handleRegionChange(region)}
                  name={region}
                  color="primary"
                />
              }
              label={region}
              key={region}
            />
          ))}
        </FormGroup>

        {/* Bookmaker Selection */}
        {availableBookmakers.length > 0 && (
          <FormGroup row style={{ marginBottom: '20px' }}>
            {/* Select All Checkbox */}
            <FormControlLabel
              control={
                <Checkbox
                  checked={
                    selectedBookmakers.length === availableBookmakers.length &&
                    availableBookmakers.length > 0
                  }
                  onChange={handleSelectAllBookmakers}
                  name="selectAll"
                  color="primary"
                />
              }
              label="Select All"
            />

            {availableBookmakers.map((bookmaker) => (
              <FormControlLabel
                control={
                  <Checkbox
                    checked={selectedBookmakers.includes(bookmaker)}
                    onChange={() => handleBookmakerChange(bookmaker)}
                    name={bookmaker}
                    color="primary"
                  />
                }
                label={bookmaker}
                key={bookmaker}
              />
            ))}
          </FormGroup>
        )}
      </header>
      <main>
        {loading && (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
            <CircularProgress />
          </Box>
        )}

        {!loading && arbitrageData.length > 0 && (
          <Grid container spacing={4} className="arbitrage-list">
            {processedArbitrageData.map((match, index) => (
              <Grid item xs={12} md={6} key={index}>
                <Card className="match-card" variant="outlined">
                  <CardContent>
                    <Typography variant="h5" component="h3" className="match-title">
                      {match.sport.toUpperCase()} - {match.event}
                    </Typography>
                    <Typography variant="body2" color="textSecondary" className="match-date">
                      {match.date !== 'N/A'
                        ? new Date(match.date).toLocaleString('en-US', {
                            weekday: 'long',
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : 'Date not available'}
                    </Typography>
                    {match.is_live && (
                      <Chip
                        label="LIVE"
                        color="secondary"
                        style={{ backgroundColor: 'red', color: 'white', marginBottom: '10px' }}
                      />
                    )}
                    <Typography
                      variant="h6"
                      component="p"
                      className="profit-info"
                      style={{ marginTop: '10px' }}
                    >
                      Potential Profit: <strong>{match.profit ? `${match.profit}%` : 'N/A'}</strong>
                    </Typography>
                    {processedArbitrageData.length > 0 && betAmount > 0 ? (
                      <List className="odds-list">
                        {match.odds.map((oddsInfo, oddsIndex) => (
                          <ListItem key={oddsIndex} className="odds-item" divider>
                            <ListItemText
                              primary={
                                <>
                                  <Typography variant="body1">
                                    <strong>{oddsInfo.team}</strong>
                                  </Typography>
                                  <Typography variant="body2" color="textSecondary">
                                    Odds: {oddsInfo.price}
                                  </Typography>
                                  <Typography variant="body2" color="textSecondary">
                                    Stake: ${oddsInfo.stakeAmount}
                                  </Typography>
                                </>
                              }
                              secondary={
                                <>
                                  <Typography variant="body2" color="textSecondary">
                                    Bookmaker: {oddsInfo.bookmaker}
                                  </Typography>
                                  {oddsInfo.link && (
                                    <Link
                                      href={oddsInfo.link}
                                      target="_blank"
                                      rel="noopener"
                                      style={{ marginTop: '5px', display: 'inline-block' }}
                                    >
                                      Place Bet
                                    </Link>
                                  )}
                                </>
                              }
                            />
                          </ListItem>
                        ))}
                      </List>
                    ) : (
                      <Typography
                        variant="body2"
                        color="textSecondary"
                        className="no-odds-message"
                        style={{ marginTop: '10px' }}
                      >
                        {betAmount > 0
                          ? 'No odds information available.'
                          : 'Please enter a valid bet amount to see stakes.'}
                      </Typography>
                    )}
                    {match.expectedReturn && betAmount > 0 && (
                      <Typography
                        variant="body2"
                        color="textSecondary"
                        className="expected-return"
                        style={{ marginTop: '10px' }}
                      >
                        Expected Return: ${match.expectedReturn}
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}

        {!loading && arbitrageData.length === 0 && (
          <Typography
            variant="body1"
            component="p"
            className="no-arbs-message"
            align="center"
            style={{ marginTop: '40px' }}
          >
            No arbitrage opportunities found.
          </Typography>
        )}
      </main>
    </Container>
  );
}

export default App;
