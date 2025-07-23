Implementation Plan
Backend (user-service):
[x] Add timezone_mode and manual_timezone fields to the user preferences model and schema.
[x] Update the preferences API and service logic to support reading and updating these fields.
[x] Add migration for the new fields (not shown here, but should be done in Alembic).
[x] Update tests for new timezone logic.
Frontend:
[x] On sign-in, fetch user preferences (using gatewayClient.getUserPreferences()).
[x] Compute the effective timezone:
effectiveTimezone = (prefs.timezone_mode === 'manual' && prefs.manual_timezone) ? prefs.manual_timezone : browserTimezone
[x] Store the effective timezone in a React context or state accessible to all components.
[x] Update all API calls (calendar, chat, etc.) to send the effective timezone.
[x] Update all display logic to use the effective timezone, not just the browser timezone.
[x] In the profile/settings UI (ProfileContent), add controls for:
    Selecting between "Automatic (browser)" and "Manual" timezone mode.
    If "Manual" is selected, show a dropdown of IANA timezones.
    Save changes to user preferences via gatewayClient.updateUserPreferences.
[x] Add tests for the new logic.