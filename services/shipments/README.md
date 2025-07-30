# Briefly Shipments Service

This service implements package shipment tracking for Briefly, including:
- Email parsing for shipping notifications
- Real-time carrier tracking integration
- Package, label, and event management APIs
- Background jobs for status updates and archiving

See [../../documentation/package_tracker_design.md](../../documentation/package_tracker_design.md) for the full technical design.

## API
/api/v1/shipments/
├── /packages                    # Package CRUD
│   ├── GET /                   # List packages
│   ├── POST /                  # Create package
│   ├── GET /{id}               # Get package by ID
│   ├── PUT /{id}               # Update package
│   ├── DELETE /{id}            # Delete package
│   └── /{id}/events            # Package-specific events
│       ├── GET /               # List events for package
│       └── POST /              # Add event to package
├── /events                     # Event management
│   ├── GET /                   # List all events
│   ├── GET /{id}               # Get event by ID
│   └── POST /from-email        # Create event from email
├── /labels                     # Label management
│   ├── GET /                   # List labels
│   ├── POST /                  # Create label
│   ├── GET /{id}               # Get label by ID
│   └── PUT /{id}               # Update label
└── /carriers                   # Carrier configurations
    ├── GET /                   # List carriers
    ├── POST /                  # Create carrier config
    ├── GET /{id}               # Get carrier by ID
    └── PUT /{id}               # Update carrier config