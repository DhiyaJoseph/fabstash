# FabStash - Inventory Management System

## Overview
FabStash is a comprehensive inventory management system designed specifically for FabLab Kerala. It helps track components, manage requests, and streamline inventory operations across electronics, mechanical, and electro-mechanical categories.

## Features

### User Roles
- **Superadmin/Admin**
  - Full access to inventory management
  - Request approval/rejection
  - Component addition and modification
  - MTM (Material Transfer Management)
  - Dashboard analytics
  
- **Regular Users**
  - Component browsing and searching
  - Request creation
  - Request status tracking
  - Personal dashboard

### Core Functionality
1. **Component Management**
   - Categorized component viewing
   - Advanced search capabilities
   - Detailed component information
   - Stock tracking

2. **Request System**
   - Component request creation
   - Status tracking
   - Request history
   - Print functionality for approved requests

3. **Dashboard**
   - Stock analytics
   - Request statistics
   - Frequently used components
   - Activity logs

## Technical Stack

### Frontend
- React.js
- Material-UI
- React Router
- Context API for state management

### Backend
- Django REST Framework
- PostgreSQL
- JWT Authentication

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd fab-stash
```

2. Install dependencies:
```bash
npm install
```

3. Create environment variables:
```bash
# Create .env file in root directory
REACT_APP_API_URL=/api
```

4. Start development server:
```bash
npm start
```

## API Endpoints

### Authentication
- `/api/login/` - User login
- `/api/google-login/` - Google OAuth login
- `/api/validate-token/` - Token validation

### Components
- `/api/components/` - Component CRUD operations
- `/api/categories/` - Category management
- `/api/subcategories/` - Subcategory management
- `/api/frequent-components/` - Frequently used components

### Requests
- `/api/requests/` - Request management
- `/api/consumer/cart/` - Cart operations
- `/api/notifications/` - Notification system

## Directory Structure

```
fab-stash/
├── src/
│   ├── assets/          # Images and static files
│   ├── components/      # Reusable React components
│   ├── context/         # Context providers
│   ├── pages/          # Page components
│   ├── styles/         # CSS files
│   └── App.js          # Main application component
├── public/             # Public assets
└── package.json        # Project dependencies
```

## Usage Guidelines

### Component Search
- Use the search bar for quick component lookup
- Filter by categories and subcategories
- View detailed component information by clicking on tiles

### Request Management
1. Add components to cart
2. Review cart contents
3. Submit request
4. Track request status in dashboard
5. Print approved requests

### Admin Operations
1. Review pending requests
2. Manage inventory levels
3. Add/modify components
4. Generate reports
5. Monitor system analytics

## Contributing
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## Support
For support and queries, please contact [support email]

## License
[License Type] - See LICENSE file for details
