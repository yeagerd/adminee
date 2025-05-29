// services/auth-service/index.js
const express = require('express');
const { getUserProfile: getMSGraphUserProfile, getUserCalendars } = require('./microsoft-graph');
const prisma = require('./prisma-client'); // Import Prisma client

const app = express();
const port = process.env.PORT || 3002; // Example port, configure as needed

app.use(express.json());

// Middleware for MS Graph token (for Graph-specific routes)
const authenticateMsGraphToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN
  if (token == null) return res.status(401).json({ error: "Microsoft Graph token is required" });
  req.msGraphToken = token;
  next();
};

// Middleware to identify user by Clerk User ID
// Assumes the calling service (e.g., API Gateway) passes 'x-user-id' header
const identifyUser = (req, res, next) => {
  const clerkUserId = req.headers['x-user-id'];
  if (!clerkUserId) {
    return res.status(400).json({ error: "Clerk User ID (x-user-id header) is required." });
  }
  req.clerkUserId = clerkUserId;
  next();
};

app.get('/', (req, res) => {
  res.send('Auth Service is running. Paths: /me (Graph), /calendars (Graph), /users/profile');
});

// Microsoft Graph specific routes
app.get('/me', authenticateMsGraphToken, async (req, res) => {
  try {
    const userProfile = await getMSGraphUserProfile(req.msGraphToken);
    res.json(userProfile);
  } catch (error) {
    console.error("Failed to get user profile from MS Graph:", error.message);
    res.status(500).json({ error: 'Failed to retrieve user profile from Microsoft Graph.', details: error.message });
  }
});

app.get('/calendars', authenticateMsGraphToken, async (req, res) => {
  try {
    const calendars = await getUserCalendars(req.msGraphToken);
    res.json(calendars);
  } catch (error) {
    console.error("Failed to get user calendars from MS Graph:", error.message);
    res.status(500).json({ error: 'Failed to retrieve user calendars from Microsoft Graph.', details: error.message });
  }
});

// User profile and settings routes (uses Clerk User ID)
app.get('/users/profile', identifyUser, async (req, res) => {
  try {
    let user = await prisma.user.findUnique({
      where: { userId: req.clerkUserId },
    });

    if (!user) {
      // Optionally, create a basic profile if one doesn't exist upon first access
      // This depends on your desired user onboarding flow
      user = await prisma.user.create({
        data: {
          userId: req.clerkUserId,
          // Initialize profileData with empty object or default settings
          profileData: {},
        }
      });
      return res.status(201).json(user); // Return 201 for newly created resource
    }
    res.json(user);
  } catch (error) {
    console.error(`Failed to get user profile for ${req.clerkUserId}:`, error.message);
    res.status(500).json({ error: 'Failed to retrieve user profile.', details: error.message });
  }
});

app.put('/users/profile', identifyUser, async (req, res) => {
  const { profileData } = req.body; // Expecting settings/profile data in a 'profileData' JSON object

  if (typeof profileData !== 'object' || profileData === null) {
    return res.status(400).json({ error: "'profileData' must be a JSON object in the request body." });
  }

  try {
    const updatedUser = await prisma.user.upsert({
      where: { userId: req.clerkUserId },
      update: { profileData: profileData }, // Overwrites existing profileData
      create: {
        userId: req.clerkUserId,
        profileData: profileData,
      },
    });
    res.json(updatedUser);
  } catch (error) {
    console.error(`Failed to update user profile for ${req.clerkUserId}:`, error.message);
    res.status(500).json({ error: 'Failed to update user profile.', details: error.message });
  }
});

// Add more routes as needed to expose other Graph API functionalities

app.listen(port, () => {
  console.log(`Auth Service listening on port ${port}`);
}); 