import { auth, clerkClient } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const { userId } = auth();

    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // The provider ID (e.g., 'oauth_microsoft') might vary based on how you named 
    // the Microsoft social connection in Clerk or Clerk's default naming.
    // Refer to Clerk documentation or your Clerk dashboard settings for the exact provider ID.
    const provider = "oauth_microsoft"; // This is a common default by Clerk for Microsoft OAuth2

    const tokenResponse = await clerkClient.users.getUserOauthAccessToken(userId, provider);

    // Check if the response has data and the data array is not empty
    if (!tokenResponse || !tokenResponse.data || tokenResponse.data.length === 0 || !tokenResponse.data[0].token) {
      console.error(`No token found for user ${userId} and provider ${provider}. User may not have connected this provider, token is missing, or API response structure is unexpected.`);
      return NextResponse.json({ error: "Microsoft Graph token not found for this user or is invalid." }, { status: 404 });
    }

    // Access the first token from the data array
    const accessToken = tokenResponse.data[0].token;

    return NextResponse.json({ accessToken });

  } catch (error) {
    console.error("Error retrieving Microsoft Graph token:", error);
    // It might be useful to log the specific error structure if it's from Clerk client
    // if (error.errors) console.error("Clerk API errors:", error.errors);
    return NextResponse.json({ error: "Internal server error while retrieving token." }, { status: 500 });
  }
} 