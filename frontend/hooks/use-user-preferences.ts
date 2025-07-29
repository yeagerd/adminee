import { useState, useEffect } from 'react';

interface UserPreferences {
  privacy: {
    shipment_data_collection: boolean;
    data_collection: boolean;
    analytics: boolean;
    personalization: boolean;
  };
  ui: {
    theme: string;
    language: string;
  };
  notifications: {
    email_notifications: boolean;
    push_notifications: boolean;
  };
}

interface UseUserPreferencesReturn {
  preferences: UserPreferences | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export const useUserPreferences = (): UseUserPreferencesReturn => {
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPreferences = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // TODO: Replace with actual API call to user service
      // For now, return default preferences
      const defaultPreferences: UserPreferences = {
        privacy: {
          shipment_data_collection: true,
          data_collection: true,
          analytics: true,
          personalization: true,
        },
        ui: {
          theme: 'system',
          language: 'en',
        },
        notifications: {
          email_notifications: true,
          push_notifications: true,
        },
      };
      
      setPreferences(defaultPreferences);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch preferences');
      // Set default preferences on error
      setPreferences({
        privacy: {
          shipment_data_collection: true,
          data_collection: true,
          analytics: true,
          personalization: true,
        },
        ui: {
          theme: 'system',
          language: 'en',
        },
        notifications: {
          email_notifications: true,
          push_notifications: true,
        },
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPreferences();
  }, []);

  return {
    preferences,
    loading,
    error,
    refetch: fetchPreferences,
  };
};

// Helper function to check if user has consented to shipment data collection
export const useShipmentDataCollectionConsent = (): boolean => {
  const { preferences } = useUserPreferences();
  return preferences?.privacy?.shipment_data_collection ?? true; // Default to true
}; 