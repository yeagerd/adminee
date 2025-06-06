const GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0';

/**
 * Calls the Microsoft Graph API.
 * @param {string} accessToken The Microsoft Graph API access token.
 * @param {string} apiPath The API path to call (e.g., '/me', '/me/calendars').
 * @param {string} method HTTP method (GET, POST, PUT, PATCH, DELETE). Defaults to GET.
 * @param {object} body Request body for POST/PUT/PATCH requests.
 * @param {object} additionalHeaders Additional headers to include.
 * @returns {Promise<object>} The JSON response from the API.
 * @throws {Error} If the API call fails or returns a non-ok status.
 */
async function callMsGraphApi(accessToken, apiPath, method = 'GET', body = null, additionalHeaders = {}) {
  if (!accessToken) {
    throw new Error("Microsoft Graph API access token is required.");
  }

  const headers = new Headers();
  headers.append("Authorization", `Bearer ${accessToken}`);
  headers.append("Content-Type", "application/json");
  for (const key in additionalHeaders) {
    headers.append(key, additionalHeaders[key]);
  }

  const options = {
    method: method,
    headers: headers,
  };

  if (body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
    options.body = JSON.stringify(body);
  }

  const url = `${GRAPH_API_ENDPOINT}${apiPath}`;

  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      const errorData = await response.text(); // Try to get more error details
      console.error("Microsoft Graph API Error:", response.status, errorData);
      throw new Error(`Microsoft Graph API request failed with status ${response.status}: ${errorData}`);
    }
    // Handle cases where response might be empty (e.g., 204 No Content)
    if (response.status === 204) {
        return null; 
    }
    return response.json();
  } catch (error) {
    console.error(`Error calling Microsoft Graph API at ${url}:`, error);
    throw error; // Re-throw the error for the caller to handle
  }
}

/**
 * Gets the signed-in user's profile information.
 * @param {string} accessToken The Microsoft Graph API access token.
 * @returns {Promise<object>} The user's profile data.
 */
async function getUserProfile(accessToken) {
  return callMsGraphApi(accessToken, '/me');
}

/**
 * Gets the signed-in user's calendars.
 * @param {string} accessToken The Microsoft Graph API access token.
 * @returns {Promise<object>} The user's calendars.
 */
async function getUserCalendars(accessToken) {
    // Example of how to request specific fields, if needed
    // return callMsGraphApi(accessToken, '/me/calendars?$select=id,name,owner');
    return callMsGraphApi(accessToken, '/me/calendars');
}

// Add more functions here for other Graph API interactions as needed, e.g.:
// - getCalendarEvents(accessToken, calendarId)
// - createCalendarEvent(accessToken, calendarId, eventData)
// - getUserMail(accessToken)
// - getUserPeople(accessToken)

module.exports = {
  callMsGraphApi,
  getUserProfile,
  getUserCalendars,
  // Export other specific functions here
}; 