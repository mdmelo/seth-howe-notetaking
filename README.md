# Plant Care Notes - Flask Application

A comprehensive Flask web application for managing plant care notes and customer information. This application allows plant care professionals to track customer information, plant conditions, treatments, and status updates.

## Features

### Customer Management
- Add new customers with contact information
- View all customers
- Track customer creation dates
- Link customers to their plant care notes

### Plant Care Notes
- Create detailed notes for each customer's plants
- Track plant/tree names, conditions, and recommended treatments
- Monitor plant status (healthy, unhealthy, treated)
- Filter notes by customer and status
- View chronological history of plant care

### Database Features
- SQLite database for reliable data storage
- Automatic database initialization
- Foreign key relationships between customers and notes
- Data integrity constraints

## Installation

1. **Clone or download the application files**

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   
   **Basic usage (default port 5000):**
   ```bash
   python app.py
   ```
   
   **Specify custom port:**
   ```bash
   python app.py --port 8080
   ```
   
   **Run with debug mode:**
   ```bash
   python app.py --debug
   ```
   
   **Specify host and port:**
   ```bash
   python app.py --host 127.0.0.1 --port 3000
   ```
   
   **All options:**
   ```bash
   python app.py --host 0.0.0.0 --port 5000 --debug
   ```

4. **Access the application:**
   Open your web browser and navigate to `http://localhost:<port>` (where `<port>` is the port you specified, default is 5000)

## Command Line Options

- `--port`, `-p`: Port to run the Flask application on (default: 5000)
- `--host`: Host to bind the Flask application to (default: 0.0.0.0)
- `--debug`: Run Flask in debug mode (enables auto-reload and detailed error messages)

## API Endpoints

### Customers
- `GET /api/customers` - Get all customers
- `POST /api/customers` - Add new customer
- `GET /api/customers/<customer_id>` - Get specific customer
- `GET /api/customers/<customer_id>/notes` - Get all notes for a customer

### Plant Notes
- `GET /api/notes` - Get all notes (with optional filters)
- `POST /api/notes` - Add new note
- `GET /api/notes/<note_id>` - Get specific note
- `PUT /api/notes/<note_id>` - Update note
- `DELETE /api/notes/<note_id>` - Delete note

### Query Parameters
- `customer_id` - Filter notes by customer
- `status` - Filter notes by status (healthy, unhealthy, treated)

## Usage Examples

### Running the Application
```bash
# Run on default port 5000
python app.py

# Run on custom port
python app.py --port 8080

# Run in debug mode on custom port
python app.py --port 3000 --debug

# Run on specific host and port
python app.py --host 127.0.0.1 --port 5000
```

### Adding a Customer
```json
POST /api/customers
{
    "name": "John Smith",
    "email": "john@example.com",
    "phone": "555-0123",
    "address": "123 Main St, City, State"
}
```

### Adding a Plant Note
```json
POST /api/notes
{
    "customer_id": "customer-uuid-here",
    "plant_name": "Japanese Maple",
    "condition": "Yellowing leaves, possible nutrient deficiency",
    "recommended_treatment": "Apply balanced fertilizer and improve drainage",
    "status": "unhealthy"
}
```

### Filtering Notes
- Get all notes for a customer: `GET /api/notes?customer_id=<customer_id>`
- Get unhealthy plants for a customer: `GET /api/notes?customer_id=<customer_id>&status=unhealthy`
- Get all treated plants: `GET /api/notes?status=treated`

## Database Schema

### Customers Table
- `id` (TEXT, PRIMARY KEY) - Unique identifier
- `name` (TEXT, NOT NULL, UNIQUE) - Customer name
- `email` (TEXT) - Email address
- `phone` (TEXT) - Phone number
- `address` (TEXT) - Physical address
- `date_created` (TEXT) - Creation timestamp

### Plant Notes Table
- `id` (TEXT, PRIMARY KEY) - Unique identifier
- `customer_id` (TEXT, FOREIGN KEY) - Reference to customer
- `customer_name` (TEXT) - Customer name for easy access
- `plant_name` (TEXT) - Name of plant/tree
- `condition` (TEXT) - Current condition description
- `recommended_treatment` (TEXT) - Treatment recommendations
- `status` (TEXT) - Status: 'healthy', 'unhealthy', or 'treated'
- `date_created` (TEXT) - Creation timestamp
- `date_updated` (TEXT) - Last update timestamp

## File Structure

```
plant-care-notes/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   └── index.html        # Web interface
└── plant_notes.db        # SQLite database (created automatically)
```

## Development

The application supports debug mode through the `--debug` flag. For production deployment:

1. Remove the `--debug` flag
2. Use a production WSGI server like Gunicorn
3. Configure proper environment variables
4. Set up database backups

## Security Considerations

- Input validation is implemented for all API endpoints
- SQL injection protection through parameterized queries
- CORS headers configured for API access
- Error handling prevents information disclosure

## Browser Compatibility

The web interface uses modern HTML5, CSS3, and JavaScript features. Compatible with:
- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## License

This application is provided as-is for educational and professional use.