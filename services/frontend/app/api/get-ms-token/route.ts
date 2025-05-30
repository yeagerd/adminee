import { getAuth, clerkClient } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = 'force-dynamic'; // Ensures the route is always dynamically rendered

export async function GET(req: NextRequest) {
  try {
    // Initialize Clerk client once, and await it
    const clerk = await clerkClient(); 
    // console.log("Initialized clerkClient, value:", clerk); // узнать, что это такое
    // if (clerk) {
    //     console.log("Available keys on clerk object:", Object.keys(clerk)); // и какие ключи у него есть
    // }

    const { userId } = getAuth(req);

    if (!userId) {
      console.log("GET /api/get-ms-token: Unauthorized, no userId from getAuth.");
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    console.log(`GET /api/get-ms-token: Authorized for userId: ${userId}`);

    // The provider ID (e.g., 'oauth_microsoft') might vary based on how you named 
    // the Microsoft social connection in Clerk or Clerk's default naming.
    // Refer to Clerk documentation or your Clerk dashboard settings for the exact provider ID.
    const provider = "microsoft"; // Removed "oauth_" prefix as per deprecation warning

    // Check if clerk.users exists before trying to use it
    if (!clerk || !clerk.users) {
        console.error("clerk.users is undefined. Clerk client might not have initialized correctly or SDK changed.", clerk);
        return NextResponse.json({ error: "Clerk client error." }, { status: 500 });
    }

    // --- Start Diagnostic Step ---
    try {
      console.log(`Attempting clerk.users.getUser(${userId})`);
      const user = await clerk.users.getUser(userId);
      console.log(`Successfully fetched user via clerk.users.getUser: ${user.id}, primary email: ${user.primaryEmailAddressId}`);
    } catch (userError) {
      console.error("Error during diagnostic clerk.users.getUser():", userError);
      // Do not immediately fail the request here, let it proceed to token fetching attempt
      // to see if that also errors or if this was the only problem point.
    }
    // --- End Diagnostic Step ---

    console.log(`Attempting clerk.users.getUserOauthAccessToken for userId: ${userId}, provider: ${provider}`);
    const tokenResponse = await clerk.users.getUserOauthAccessToken(userId, provider);

    if (!tokenResponse || !tokenResponse.data || tokenResponse.data.length === 0 || !tokenResponse.data[0].token) {
      console.error(`No token found for user ${userId} and provider ${provider}. Full response:`, JSON.stringify(tokenResponse));
      return NextResponse.json({ error: "Microsoft Graph token not found for this user or is invalid." }, { status: 404 });
    }

    const accessToken = tokenResponse.data[0].token;
    console.log(`Successfully fetched MS Graph access token for userId: ${userId}`);
    return NextResponse.json({ accessToken });

  } catch (error) {
    console.error("Error in GET /api/get-ms-token route:", error);
    // It might be useful to log the specific error structure if it's from Clerk client
    // if (error.errors) console.error("Clerk API errors:", error.errors);
    return NextResponse.json({ error: "Internal server error while retrieving token." }, { status: 500 });
  }
} 