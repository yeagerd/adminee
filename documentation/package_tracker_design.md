# Package Shipment Tracker - Technical Design Document

## 1. Overview

This document outlines the technical design for adding package shipment tracking functionality to our existing full-stack application. The feature will automatically detect shipping notifications from emails and provide users with consolidated package tracking information, similar to the discontinued Slice service.

## 2. Requirements

### 2.1 Functional Requirements
- **Email Parsing**: Automatically detect and parse shipping confirmation emails from major carriers (UPS, FedEx, USPS, DHL, Amazon)
- **Tracking Integration**: Fetch real-time tracking status from carrier APIs
- **User Interface**: Display consolidated package tracking dashboard
- **Labels**: Allow users to create custom labels and attach them to packages for organization
- **Manual Entry**: Allow users to manually add tracking numbers
- **Archive Management**: Automatically archive delivered packages after 30 days

### 2.2 Non-Functional Requirements
- **Performance**: Package status updates within 5 minutes of carrier updates
- **Reliability**: 99.5% uptime for tracking services
- **Security**: Encrypted storage of tracking data and email content
- **Scalability**: Support up to 10,000 active packages across all users

## 3. Architecture Overview

### 3.1 System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Email Client  │    │  Package API    │    │   Frontend UI   │
│   Integration   │    │   Gateway       │    │   Dashboard     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌─────────────────────────────────────────────────┐
         │              Core Application                   │
         │  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
         │  │   Email     │  │  Tracking   │  │ Package  │ │
         │  │  Parser     │  │   Service   │  │ Manager  │ │
         │  │   Service   │  │             │  │          │ │
         │  └─────────────┘  └─────────────┘  └──────────┘ │
         └─────────────────────────────────────────────────┘
                                 │
         ┌─────────────────────────────────────────────────┐
         │                Database Layer                   │
         │  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
         │  │   Users     │  │  Packages   │  │  Email   │ │
         │  │   Table     │  │    Table    │  │  Cache   │ │
         │  └─────────────┘  └─────────────┘  └──────────┘ │
         └─────────────────────────────────────────────────┘
```

## 4. Database Design

### 4.1 New Tables

#### packages
```sql
CREATE TABLE packages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    tracking_number VARCHAR(255) NOT NULL,
    carrier VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    estimated_delivery DATE,
    actual_delivery DATE,
    recipient_name VARCHAR(255),
    recipient_address TEXT,
    shipper_name VARCHAR(255),
    package_description TEXT,
    order_number VARCHAR(255), -- Order number from retailer (e.g., Amazon order ID)
    tracking_link VARCHAR(500), -- Direct tracking URL from carrier or retailer
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    archived_at TIMESTAMP,
    email_message_id VARCHAR(255), -- Link to original email
    UNIQUE(user_id, tracking_number, carrier)
);
```

#### tracking_events
```sql
CREATE TABLE tracking_events (
    id SERIAL PRIMARY KEY,
    package_id INTEGER REFERENCES packages(id),
    event_date TIMESTAMP NOT NULL,
    status VARCHAR(100) NOT NULL,
    location VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### labels
```sql
CREATE TABLE labels (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    color VARCHAR(7) DEFAULT '#3B82F6', -- Hex color code
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)
);
```

#### package_labels
```sql
CREATE TABLE package_labels (
    id SERIAL PRIMARY KEY,
    package_id INTEGER REFERENCES packages(id),
    label_id INTEGER REFERENCES labels(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(package_id, label_id)
);
```

#### carrier_configs
```sql
CREATE TABLE carrier_configs (
    id SERIAL PRIMARY KEY,
    carrier_name VARCHAR(50) NOT NULL,
    api_endpoint VARCHAR(255),
    rate_limit_per_hour INTEGER DEFAULT 1000,
    is_active BOOLEAN DEFAULT true,
    email_patterns JSONB, -- Store regex patterns for email detection
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 5. API Design

### 5.1 REST Endpoints

#### Package Management
```
GET    /api/packages                    - List user's packages (supports label filtering)
POST   /api/packages                    - Add package manually
GET    /api/packages/:id                - Get package details
PUT    /api/packages/:id                - Update package
DELETE /api/packages/:id                - Delete package
POST   /api/packages/:id/refresh        - Force refresh tracking
POST   /api/packages/:id/labels         - Add label to package
DELETE /api/packages/:id/labels/:labelId - Remove label from package
```

#### Label Management
```
GET    /api/labels                      - List user's labels
POST   /api/labels                      - Create new label
PUT    /api/labels/:id                  - Update label
DELETE /api/labels/:id                  - Delete label
```

#### Tracking
```
GET    /api/packages/:id/events         - Get tracking events
POST   /api/tracking/webhook            - Webhook for carrier updates
```

### 5.2 Request/Response Examples

#### GET /api/packages
```json
{
  "data": [
    {
      "id": 123,
      "tracking_number": "1Z999AA1234567890",
      "carrier": "UPS",
      "status": "In Transit",
      "estimated_delivery": "2024-03-15",
      "recipient_name": "John Doe",
      "shipper_name": "Amazon",
      "package_description": "Electronics",
      "order_number": "123-4567890-1234567",
      "tracking_link": "https://www.ups.com/track?tracknum=1Z999AA1234567890",
      "updated_at": "2024-03-13T10:30:00Z",
      "events_count": 5,
      "labels": [
        {
          "id": 1,
          "name": "project_x",
          "color": "#3B82F6"
        },
        {
          "id": 3,
          "name": "personal",
          "color": "#10B981"
        }
      ]
    }
  ],
  "pagination": {
    "next_cursor": "eyJsYXN0X2lkIjoiMTIzNDU2Nzg5MC1hYmNkLWVmZ2gtaWprbC1tbm9wIiwibGFzdF91cGRhdGVkIjoiMjAyNC0wMy0xM1QxMDozMDowMFoiLCJmaWx0ZXJzIjp7fSwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoyMH0=",
    "prev_cursor": null,
    "has_next": true,
    "has_prev": false,
    "limit": 20
  }
}
```

#### POST /api/labels
```json
// Request
{
  "name": "project_x",
  "color": "#3B82F6"
}

// Response
{
  "id": 1,
  "name": "project_x",
  "color": "#3B82F6",
  "created_at": "2024-03-13T10:30:00Z"
}
```

#### GET /api/packages?labels=project_x,urgent
```json
{
  "data": [
    // Only packages with "project_x" OR "urgent" labels
  ],
  "filters": {
    "labels": ["project_x", "urgent"]
  }
}
```

## 6. Email Integration

### 6.1 Email Parsing Strategy

#### Detection Patterns
```javascript
const CARRIER_PATTERNS = {
  UPS: {
    subject: /ups.*ship|track.*ups/i,
    tracking: /1Z[0-9A-Z]{16}/g,
    order_pattern: /order.*#?([A-Z0-9\-]+)/i,
    tracking_link_pattern: /(https?:\/\/[^\s]*ups\.com[^\s]*)/i
  },
  FEDEX: {
    subject: /fedex.*ship|track.*fedex/i,
    tracking: /\b[0-9]{12,14}\b/g,
    order_pattern: /order.*#?([A-Z0-9\-]+)/i,
    tracking_link_pattern: /(https?:\/\/[^\s]*fedex\.com[^\s]*)/i
  },
  USPS: {
    subject: /usps.*ship|postal.*track/i,
    tracking: /\b[0-9]{20,22}\b/g,
    order_pattern: /order.*#?([A-Z0-9\-]+)/i,
    tracking_link_pattern: /(https?:\/\/[^\s]*usps\.com[^\s]*)/i
  },
  AMAZON: {
    subject: /amazon.*ship|your.*order.*ship/i,
    tracking: /1Z[0-9A-Z]{16}|\b[0-9]{12,14}\b|\b[0-9]{20,22}\b/g,
    order_pattern: /order.*#([A-Z0-9\-]+)/i,
    tracking_link_pattern: /(https?:\/\/[^\s]*amazon\.com[^\s]*track[^\s]*)/i
  }
};
```

#### Email Processing Flow
1. Email webhook triggers parsing service
2. Extract sender, subject, and body content
3. Match against carrier patterns
4. Extract tracking numbers using regex
5. Extract order numbers and tracking links using regex patterns
6. Parse shipping details (recipient, estimated delivery)
7. Create or update package records with order_number and tracking_link
8. Queue initial tracking status fetch

### 6.2 Integration Points

Since the app already has Google/Microsoft email integration:

```javascript
// Extend existing email service
class EmailService {
  // ... existing methods
  
  async processShippingEmail(email) {
    const parsedData = await this.parseShippingNotification(email);
    if (parsedData) {
      await this.packageService.createFromEmail(parsedData);
    }
  }
}
```

## 7. Carrier API Integration

### 7.1 Unified Tracking Interface

```javascript
class TrackingService {
  async getTrackingInfo(carrier, trackingNumber) {
    const handler = this.getCarrierHandler(carrier);
    return await handler.track(trackingNumber);
  }
  
  getCarrierHandler(carrier) {
    const handlers = {
      'UPS': new UPSHandler(),
      'FEDEX': new FedexHandler(),
      'USPS': new USPSHandler()
    };
    return handlers[carrier];
  }
}
```

### 7.2 Rate Limiting and Caching

```javascript
class CarrierAPI {
  constructor(carrier) {
    this.rateLimiter = new RateLimiter(1000, 'hour'); // 1000 requests/hour
    this.cache = new Redis();
  }
  
  async track(trackingNumber) {
    const cacheKey = `tracking:${this.carrier}:${trackingNumber}`;
    
    // Check cache first (TTL: 15 minutes)
    const cached = await this.cache.get(cacheKey);
    if (cached) return JSON.parse(cached);
    
    // Rate limit check
    await this.rateLimiter.consume();
    
    const result = await this.fetchFromAPI(trackingNumber);
    await this.cache.setex(cacheKey, 900, JSON.stringify(result));
    
    return result;
  }
}
```

## 8. Background Jobs

### 8.1 Job Types

```javascript
// Update tracking information
class TrackingUpdateJob {
  async perform(packageId) {
    const package = await Package.findById(packageId);
    if (!package || package.status === 'delivered') return;
    
    const trackingInfo = await this.trackingService.getTrackingInfo(
      package.carrier, 
      package.tracking_number
    );
    
    await this.updatePackageStatus(package, trackingInfo);
  }
}

// Archive delivered packages
class ArchivePackagesJob {
  async perform() {
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    
    await Package.update(
      { archived_at: new Date() },
      {
        where: {
          status: 'delivered',
          actual_delivery: { [Op.lt]: thirtyDaysAgo },
          archived_at: null
        }
      }
    );
  }
}
```

### 8.2 Job Scheduling

```javascript
// Schedule tracking updates every 30 minutes for active packages
cron.schedule('*/30 * * * *', async () => {
  const activePackages = await Package.findAll({
    where: { 
      status: { [Op.notIn]: ['delivered', 'cancelled'] },
      archived_at: null
    }
  });
  
  for (const pkg of activePackages) {
    jobQueue.add('tracking-update', { packageId: pkg.id });
  }
});
```

## 9. Frontend Implementation

### 9.1 Component Structure

```
src/components/packages/
├── PackageDashboard.jsx
├── PackageList.jsx
├── PackageCard.jsx
├── PackageDetails.jsx
├── TrackingTimeline.jsx
├── AddPackageModal.jsx
├── PackageFilters.jsx
├── LabelManager.jsx
├── LabelPicker.jsx
└── LabelChip.jsx
```

### 9.2 State Management

```javascript
// Redux slice for packages
const packagesSlice = createSlice({
  name: 'packages',
  initialState: {
    items: [],
    loading: false,
    filters: { 
      status: 'all', 
      carrier: 'all',
      labels: [] 
    }
  },
  reducers: {
    setPackages: (state, action) => {
      state.items = action.payload;
    },
    updatePackage: (state, action) => {
      const index = state.items.findIndex(p => p.id === action.payload.id);
      if (index >= 0) {
        state.items[index] = action.payload;
      }
    },
    setLabelFilter: (state, action) => {
      state.filters.labels = action.payload;
    }
  }
});

// Labels slice
const labelsSlice = createSlice({
  name: 'labels',
  initialState: {
    items: [],
    loading: false
  },
  reducers: {
    setLabels: (state, action) => {
      state.items = action.payload;
    },
    addLabel: (state, action) => {
      state.items.push(action.payload);
    },
    updateLabel: (state, action) => {
      const index = state.items.findIndex(l => l.id === action.payload.id);
      if (index >= 0) {
        state.items[index] = action.payload;
      }
    },
    removeLabel: (state, action) => {
      state.items = state.items.filter(l => l.id !== action.payload);
    }
  }
});
```

### 9.3 Label Components

```javascript
// LabelChip component for displaying labels
const LabelChip = ({ label, onRemove, removable = false }) => {
  return (
    <span 
      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
      style={{ backgroundColor: label.color + '20', color: label.color }}
    >
      {label.name}
      {removable && (
        <button
          onClick={() => onRemove(label.id)}
          className="ml-1 hover:bg-gray-200 rounded-full p-0.5"
        >
          ×
        </button>
      )}
    </span>
  );
};

// PackageFilters component with label filtering
const PackageFilters = ({ filters, onFiltersChange, labels }) => {
  return (
    <div className="flex gap-4 mb-4">
      <select 
        value={filters.status} 
        onChange={(e) => onFiltersChange({...filters, status: e.target.value})}
      >
        <option value="all">All Statuses</option>
        <option value="in_transit">In Transit</option>
        <option value="delivered">Delivered</option>
      </select>
      
      <select 
        value={filters.carrier}
        onChange={(e) => onFiltersChange({...filters, carrier: e.target.value})}
      >
        <option value="all">All Carriers</option>
        <option value="UPS">UPS</option>
        <option value="FEDEX">FedEx</option>
        <option value="USPS">USPS</option>
      </select>
      
      <div className="flex-1">
        <LabelPicker
          selectedLabels={filters.labels}
          availableLabels={labels}
          onChange={(selectedLabels) => 
            onFiltersChange({...filters, labels: selectedLabels})
          }
          placeholder="Filter by labels..."
        />
      </div>
    </div>
  );
};

// LabelPicker for selecting multiple labels
const LabelPicker = ({ selectedLabels, availableLabels, onChange, placeholder }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  const toggleLabel = (labelId) => {
    const newSelection = selectedLabels.includes(labelId)
      ? selectedLabels.filter(id => id !== labelId)
      : [...selectedLabels, labelId];
    onChange(newSelection);
  };
  
  return (
    <div className="relative">
      <div 
        className="border rounded-md p-2 cursor-pointer min-h-[40px]"
        onClick={() => setIsOpen(!isOpen)}
      >
        {selectedLabels.length === 0 ? (
          <span className="text-gray-400">{placeholder}</span>
        ) : (
          <div className="flex flex-wrap gap-1">
            {selectedLabels.map(labelId => {
              const label = availableLabels.find(l => l.id === labelId);
              return label ? (
                <LabelChip 
                  key={labelId} 
                  label={label} 
                  onRemove={() => toggleLabel(labelId)}
                  removable
                />
              ) : null;
            })}
          </div>
        )}
      </div>
      
      {isOpen && (
        <div className="absolute z-10 w-full bg-white border rounded-md shadow-lg mt-1">
          {availableLabels.map(label => (
            <div
              key={label.id}
              className="p-2 hover:bg-gray-100 cursor-pointer flex items-center"
              onClick={() => toggleLabel(label.id)}
            >
              <input
                type="checkbox"
                checked={selectedLabels.includes(label.id)}
                readOnly
                className="mr-2"
              />
              <LabelChip label={label} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

### 9.4 Real-time Updates

```javascript
// WebSocket integration for live updates
useEffect(() => {
  const ws = new WebSocket(`/ws/packages/${userId}`);
  
  ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    if (update.type === 'package_status_changed') {
      dispatch(updatePackage(update.package));
    }
  };
  
  return () => ws.close();
}, [userId]);
```

## 10. Security Considerations

### 10.1 Data Protection
- Encrypt sensitive package information (addresses, recipient names)
- Implement user-based access controls for package data
- Sanitize all email content before parsing
- Use HTTPS for all carrier API communications

### 10.2 Privacy
- Allow users to delete package history
- Anonymize tracking data in analytics
- Provide opt-out mechanism for email parsing

## 11. Testing Strategy

### 11.1 Unit Tests
- Email parsing logic with various email formats
- Carrier API handlers with mock responses
- Database operations and data validation

### 11.2 Integration Tests
- End-to-end email processing flow
- API endpoint functionality
- Background job execution

### 11.3 Test Data
```javascript
// Mock shipping email for testing
const mockShippingEmail = {
  from: 'auto-confirm@amazon.com',
  subject: 'Your order has shipped',
  body: `
    Your order #123-4567890-1234567 has shipped.
    Tracking Number: 1Z999AA1234567890
    Carrier: UPS
    Estimated Delivery: March 15, 2024
    Track your package: https://www.amazon.com/gp/track?tracking_id=1Z999AA1234567890
  `
};
```

## 12. Monitoring and Analytics

### 12.1 Key Metrics
- Email parsing accuracy rate
- Carrier API response times and error rates
- Package status update frequency
- User engagement with tracking features

### 12.2 Logging
```javascript
// Structured logging for package operations
logger.info('Package created from email', {
  userId: user.id,
  trackingNumber: package.tracking_number,
  carrier: package.carrier,
  source: 'email_parsing'
});
```

## 13. Deployment Considerations

### 13.1 Database Migration
```sql
-- Run migrations in order
-- 1. Create new tables
-- 2. Add indexes for performance
CREATE INDEX idx_packages_user_status ON packages(user_id, status);
CREATE INDEX idx_packages_tracking ON packages(tracking_number, carrier);
CREATE INDEX idx_tracking_events_package_date ON tracking_events(package_id, event_date);
CREATE INDEX idx_labels_user ON labels(user_id);
CREATE INDEX idx_package_labels_package ON package_labels(package_id);
CREATE INDEX idx_package_labels_label ON package_labels(label_id);
```

### 13.2 Feature Rollout
1. Deploy backend changes with feature flag disabled
2. Run database migrations
3. Deploy frontend changes
4. Enable feature for beta users (10%)
5. Monitor metrics and error rates
6. Gradual rollout to 50%, then 100%

## 14. Future Enhancements

### 14.1 Phase 2 Features
- Package photo uploads and organization
- Delivery preferences and instructions
- Integration with calendar for delivery scheduling
- Package sharing with family members
- International shipping support
- Label templates and auto-labeling rules

### 14.2 Machine Learning Opportunities
- Improved email parsing accuracy using ML models
- Delivery prediction based on historical data
- Anomaly detection for delayed packages
- Smart categorization of package types

## 15. Implementation Timeline

### Week 1-2: Foundation
- Database schema design and migration
- Basic API endpoints
- Email parsing service

### Week 3-4: Core Features
- Carrier API integrations
- Background job system
- Frontend dashboard

### Week 5-6: Polish
- Real-time updates
- Error handling and logging
- Testing and bug fixes

### Week 7: Deployment
- Production deployment
- Monitoring setup
- Beta user rollout

This design provides a solid foundation for adding package tracking functionality while leveraging the existing email integration capabilities of your application.