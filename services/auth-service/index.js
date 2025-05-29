// services/auth-service/index.js
const express = require('express');
const { getUserProfile, getUserCalendars } = require('./microsoft-graph');

const app = express();
const port = process.env.PORT || 3002; // Example port, configure as needed

app.use(express.json());

// Middleware to check for Authorization header (Bearer token)
// This token would be the MS Graph Access Token, passed from the service calling auth-service
// (e.g., from the Next.js API Gateway after retrieving it via Clerk)
const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

  if (token == null) return res.sendStatus(401); // if there's no token

  req.msGraphToken = token;
  next();
};

app.get('/', (req, res) => {
  res.send('Auth Service is running. Use /me or /calendars with a Bearer token for MS Graph.');
});

app.get('/me', authenticateToken, async (req, res) => {
  try {
    const userProfile = await getUserProfile(req.msGraphToken);
    res.json(userProfile);
  } catch (error) {
    console.error("Failed to get user profile:", error.message);
    res.status(500).json({ error: 'Failed to retrieve user profile from Microsoft Graph.', details: error.message });
  }
});

app.get('/calendars', authenticateToken, async (req, res) => {
  try {
    const calendars = await getUserCalendars(req.msGraphToken);
    res.json(calendars);
  } catch (error) {
    console.error("Failed to get user calendars:", error.message);
    res.status(500).json({ error: 'Failed to retrieve user calendars from Microsoft Graph.', details: error.message });
  }
});

// Add more routes as needed to expose other Graph API functionalities

app.listen(port, () => {
  console.log(`Auth Service listening on port ${port}`);
}); 