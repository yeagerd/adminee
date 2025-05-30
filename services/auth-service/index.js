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

// User profile and settings routes
app.get('/users/profile', identifyUser, async (req, res) => {
  try {
    let user = await prisma.user.findUnique({
      where: { clerkUserId: req.clerkUserId }, // Changed from userId to clerkUserId
    });

    if (!user) {
      // Create a user profile if one doesn't exist
      user = await prisma.user.create({
        data: {
          clerkUserId: req.clerkUserId,
          email: req.body.email, // Optional: attempt to get email from Clerk user object if passed by gateway
          userSettings: { timezone: 'UTC' }, // Default timezone
          calendarProvider: null,
        }
      });
      return res.status(201).json(user);
    }
    res.json(user);
  } catch (error) {
    console.error(`Failed to get user profile for ${req.clerkUserId}:`, error.message);
    res.status(500).json({ error: 'Failed to retrieve user profile.', details: error.message });
  }
});

app.put('/users/profile', identifyUser, async (req, res) => {
  const { email, name, calendarProvider, userSettings, profileData } = req.body;

  const dataToUpdate = {};
  if (email !== undefined) dataToUpdate.email = email;
  if (name !== undefined) dataToUpdate.name = name;
  if (profileData !== undefined) dataToUpdate.profileData = profileData; // Keep support for generic profileData

  if (calendarProvider !== undefined) {
    if (calendarProvider === null || ["microsoft", "google"].includes(calendarProvider.toLowerCase())) {
      dataToUpdate.calendarProvider = calendarProvider;
    } else {
      return res.status(400).json({ error: "Invalid calendarProvider. Allowed values: 'microsoft', 'google', or null." });
    }
  }

  if (userSettings !== undefined) {
    if (typeof userSettings !== 'object' || userSettings === null) {
      return res.status(400).json({ error: "'userSettings' must be a JSON object." });
    }
    // Basic validation for timezone if provided - can be expanded
    if (userSettings.timezone !== undefined) {
      try {
        // Check if it's a somewhat valid timezone string. Node's Intl doesn't validate IANA IDs directly.
        // For robust validation, a library like moment-timezone or jstimezonedetect might be used, or keep it simple.
        new Intl.DateTimeFormat(undefined, { timeZone: userSettings.timezone });
      } catch (tzError) {
        return res.status(400).json({ error: `Invalid timezone string: ${userSettings.timezone}` });
      }
    }
    dataToUpdate.userSettings = userSettings;
  }
  
  if (Object.keys(dataToUpdate).length === 0) {
    return res.status(400).json({ error: "No valid fields provided for update." });
  }

  try {
    const updatedUser = await prisma.user.upsert({
      where: { clerkUserId: req.clerkUserId }, // Changed from userId to clerkUserId
      update: dataToUpdate,
      create: {
        clerkUserId: req.clerkUserId,
        email: email,
        name: name,
        calendarProvider: calendarProvider,
        userSettings: userSettings,
        profileData: profileData
      },
    });
    res.json(updatedUser);
  } catch (error) {
    console.error(`Failed to update user profile for ${req.clerkUserId}:`, error.message);
    if (error.code === 'P2002') { // Unique constraint failed (e.g. email)
        return res.status(409).json({ error: 'Failed to update profile. A user with the provided email may already exist.', field: error.meta?.target?.join(',') });
    }
    res.status(500).json({ error: 'Failed to update user profile.', details: error.message });
  }
});

// Add more routes as needed to expose other Graph API functionalities

app.listen(port, () => {
  console.log(`Auth Service listening on port ${port}`);
}); 