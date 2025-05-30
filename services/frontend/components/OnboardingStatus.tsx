"use client";

import { useEffect, useState } from 'react';
import { useUser } from '@clerk/nextjs';

export default function OnboardingStatus() {
  const { isSignedIn, user } = useUser();
  const [msTokenStatus, setMsTokenStatus] = useState<'loading' | 'connected' | 'not_connected' | 'error'>('loading');
  const [errorDetails, setErrorDetails] = useState<string | null>(null);

  useEffect(() => {
    if (isSignedIn) {
      const checkToken = async () => {
        try {
          setMsTokenStatus('loading');
          setErrorDetails(null);
          const response = await fetch('/api/get-ms-token');
          if (response.ok) {
            const data = await response.json();
            if (data.accessToken) {
              setMsTokenStatus('connected');
            } else {
              // This case might happen if the API returns 200 but no token, though our API sends 404
              setMsTokenStatus('not_connected'); 
            }
          } else if (response.status === 404) {
            setMsTokenStatus('not_connected');
            const errorData = await response.json();
            setErrorDetails(errorData.error || "Microsoft account not connected or scopes not granted.");
          } else {
            setMsTokenStatus('error');
            const errorData = await response.json();
            setErrorDetails(errorData.error || "Failed to check Microsoft token status.");
          }
        } catch (err) {
          console.error("Error checking MS token status:", err);
          setMsTokenStatus('error');
          setErrorDetails(err instanceof Error ? err.message : "An unknown error occurred.");
        }
      };
      checkToken();
    }
  }, [isSignedIn, user]); // Re-check if user session changes

  if (!isSignedIn) {
    return null; // Or a message prompting sign-in, but SignedOut in layout handles this
  }

  if (msTokenStatus === 'loading') {
    return <p>Checking Microsoft Account connection...</p>;
  }

  if (msTokenStatus === 'error') {
    return (
      <div style={{ color: 'red', border: '1px solid red', padding: '10px', margin: '10px 0' }}>
        <p>Error checking Microsoft Account connection.</p>
        {errorDetails && <p>Details: {errorDetails}</p>}
        <p>Please try managing your account connections via your user profile button (top right) or refresh the page.</p>
      </div>
    );
  }

  if (msTokenStatus === 'connected') {
    return (
      <div style={{ color: 'green', border: '1px solid green', padding: '10px', margin: '10px 0' }}>
        <p>Your Microsoft Account is connected and required permissions seem to be granted.</p>
        <p>Briefly can now access your calendar and other Microsoft services as needed.</p>
      </div>
    );
  }

  // msTokenStatus === 'not_connected'
  return (
    <div style={{ color: 'orange', border: '1px solid orange', padding: '10px', margin: '10px 0' }}>
      <p><strong>Action Required:</strong> Connect your Microsoft Account or ensure all permissions are granted.</p>
      {errorDetails && <p>Details: {errorDetails}</p>}
      <p>
        Please use the User Profile button (top right), navigate to "Manage Account", 
        then "Connected Accounts" to connect your Microsoft account or verify permissions.
      </p>
      <p>Briefly needs access to your Microsoft calendar and services to provide its full functionality.</p>
    </div>
  );
} 