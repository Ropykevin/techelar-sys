# WordPress Course Platform

A Flask-based web application for managing WordPress course registrations and payments.

## Features

- Responsive landing page with course information and testimonials
- Course registration form with multiple duration options
- Secure checkout process with payment integration
- SQLite database for storing registrations and payment information
- Bootstrap-based responsive design
- Flash messaging for user feedback

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd wordpress-course-platform
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Make sure your virtual environment is activated

2. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to `http://localhost:5000`

## Project Structure

```
wordpress-course-platform/
├── app.py                 # Main application file
├── requirements.txt       # Python dependencies
├── static/               # Static files
│   └── css/
│       └── style.css     # Custom CSS styles
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── index.html        # Landing page
│   ├── register.html     # Registration form
│   ├── checkout.html     # Checkout page
│   └── confirmation.html # Confirmation page
└── instance/            # Instance-specific files
    └── wordpress_courses.db  # SQLite database
```

## Development

- The application uses Flask-SQLAlchemy for database operations
- Bootstrap 5 for responsive design
- Custom CSS for additional styling
- Flash messages for user feedback
- Form validation and error handling

## Security Notes

- The application uses a secure secret key for session management
- Form validation is implemented for all user inputs
- Payment processing is currently mocked (replace with real payment gateway in production)
- Database operations use parameterized queries to prevent SQL injection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.