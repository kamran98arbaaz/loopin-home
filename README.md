# LoopIn

**A modern, professional web application for team updates and communication.**

LoopIn is a comprehensive team communication platform designed to streamline updates, track progress, and maintain organizational knowledge through SOP summaries and lessons learned.

## ✨ Key Features

### 🔔 Real-time Notifications
- **Bell Icon System**: Pulsing red badge for new updates within 24 hours
- **Updates Banner**: Dropdown showing 3 most recent updates with "View All" option
- **Sound Notifications**: Audio alerts for new updates
- **Live Updates**: Socket.IO powered real-time communication

### 📝 Update Management
- **Create Updates**: Rich text updates with process categorization
- **Edit/Delete**: Full CRUD operations with proper authentication
- **Browse Updates**: Clean, modern card-based interface with read counts
- **Search**: Enhanced search functionality across all updates

### 👥 User Management
- **Secure Authentication**: Flask-Login with session management
- **User Registration**: Simplified registration without help text clutter
- **Display Names**: Professional user identification system

### 📚 Knowledge Management
- **SOP Summaries**: Standard Operating Procedure documentation
- **Lessons Learned**: Capture and share organizational learning
- **Search Integration**: Find knowledge across all content types

### 🎨 Modern UI/UX
- **Professional Design**: Clean, modern interface with consistent styling
- **Responsive Layout**: Works seamlessly on desktop and mobile devices
- **Visual Indicators**: Pulsing badges and clear status indicators
- **Intuitive Navigation**: User-friendly interface with logical flow

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd loopin_railway_clean_deploy
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   # Create a .env file or set environment variables
   DATABASE_URL=postgresql://username:password@localhost/loopin
   SECRET_KEY=your-secret-key-here
   FLASK_ENV=development
   ```

4. **Initialize the database:**
   ```bash
   python init_db.py
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```

6. **Access the application:**
   Open your browser and navigate to `http://localhost:5000`

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Yes | `postgresql://user:pass@localhost/loopin` |
| `TEST_DATABASE_URL` | Test database connection string | No | `postgresql://user:pass@localhost/loopin_test` |
| `FLASK_SECRET_KEY` | Flask secret key for sessions | Yes | `your-super-secret-key` |
| `FLASK_ENV` | Environment (development/production/testing) | No | `production` |
| `TESTING` | Enable testing mode (true/false) | No | `false` |
| `PORT` | Port number (default: 8000) | No | `8000` |

### Database Setup

The application uses PostgreSQL with SQLAlchemy ORM. Database migrations are handled through Flask-Migrate.

```bash
# Create migration
flask db migrate -m "Description"

# Apply migration
flask db upgrade
```

### Testing Setup

**🔒 IMPORTANT: Tests now use a separate database to protect production data!**

1. **Create test database:**
   ```bash
   # PostgreSQL
   createdb loopin_test

   # Or use SQLite (automatic fallback)
   # No setup needed - will create test_loopin.db automatically
   ```

2. **Set test environment variables:**
   ```bash
   # Option 1: Set in .env file
   TEST_DATABASE_URL=postgresql://username:password@localhost/loopin_test

   # Option 2: Set for single test run
   TESTING=true python -m pytest
   ```

3. **Run tests safely:**
   ```bash
   # Using the test helper
   python test_config.py run

   # Or manually
   TESTING=true python -m pytest

   # Or set environment and run
   export TESTING=true
   python -m pytest
   ```

## 🏗️ Architecture

### Backend
- **Framework**: Flask with Blueprint architecture
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Flask-Login with secure session management
- **Real-time**: Socket.IO for live notifications
- **API**: RESTful endpoints for frontend integration

### Frontend
- **Templates**: Jinja2 with modern HTML5 structure
- **Styling**: Custom CSS with CSS variables and responsive design
- **JavaScript**: Modular ES6+ code with proper error handling
- **Assets**: Optimized images, sounds, and stylesheets

### Key Components
- **User Management**: Registration, login, session handling
- **Update System**: CRUD operations with real-time notifications
- **Search Engine**: Full-text search across all content
- **Knowledge Base**: SOP summaries and lessons learned
- **Notification System**: Bell icon with badge and banner

## 🚀 Deployment

### Railway Deployment

This application is optimized for Railway deployment:

1. **Connect Repository**: Link your Git repository to Railway
2. **Environment Variables**: Set required environment variables in Railway dashboard
3. **Database**: Add PostgreSQL service in Railway
4. **Deploy**: Railway will automatically deploy on push to main branch

### Production Checklist

- [x] Environment variables configured
- [x] Database migrations applied
- [x] Static assets optimized
- [x] Error handling implemented
- [x] Security measures in place
- [x] Performance optimized

## 📱 Usage

### For Users
1. **Register/Login**: Create account or sign in
2. **Post Updates**: Share progress and updates with your team
3. **Browse Updates**: View team updates with visual indicators for new content
4. **Search**: Find specific updates or information quickly
5. **Notifications**: Stay informed with real-time alerts

### For Administrators
1. **User Management**: Monitor user activity and manage accounts
2. **Content Moderation**: Edit or remove inappropriate content
3. **Knowledge Management**: Organize SOPs and lessons learned
4. **System Monitoring**: Track application health and performance

## 🔒 Security Features

- **CSRF Protection**: Enabled for all forms
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **Session Security**: Secure session management with Flask-Login
- **Input Validation**: Comprehensive input sanitization
- **Authentication**: Proper user authentication and authorization

## 🎯 Recent Updates

### Latest Features (2025)
- ✅ **Bell Icon System**: Restored with badge and updates banner
- ✅ **Update Card Improvements**: Read count repositioned, NEW badges removed
- ✅ **Modern Edit Page**: Professional design with enhanced UI
- ✅ **Browse Updates Badge**: 24-hour pulsing red dot indicator
- ✅ **Banner Optimization**: Limited to 3 updates with "View All" option
- ✅ **Clean Architecture**: Removed unnecessary files and dependencies
- ✅ **Production Ready**: Comprehensive testing and optimization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 📞 Support

For support and questions, please contact the development team.

---

**LoopIn 2025** - Streamlining team communication and knowledge management.
