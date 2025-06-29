from flask import Flask, request, jsonify, render_template
import sqlite3
import uuid
from datetime import datetime
import os
import argparse

app = Flask(__name__)

# Database configuration
DATABASE = 'plant_notes.db'

def get_db_connection():
    """Get database connection with row factory for dict-like access"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    
    # Create customers table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            email TEXT,
            phone TEXT,
            address TEXT,
            date_created TEXT NOT NULL
        )
    ''')
    
    # Create plant_notes table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS plant_notes (
            id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            plant_name TEXT NOT NULL,
            condition TEXT NOT NULL,
            recommended_treatment TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('healthy', 'unhealthy', 'treated')),
            date_created TEXT NOT NULL,
            date_updated TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/customers', methods=['GET', 'POST'])
def customers():
    """Handle customer operations"""
    if request.method == 'POST':
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({'error': 'Customer name is required'}), 400
        
        customer_id = str(uuid.uuid4())
        date_created = datetime.now().isoformat()
        
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO customers (id, name, email, phone, address, date_created)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (customer_id, data['name'], data.get('email'), 
                  data.get('phone'), data.get('address'), date_created))
            conn.commit()
            
            customer = {
                'id': customer_id,
                'name': data['name'],
                'email': data.get('email'),
                'phone': data.get('phone'),
                'address': data.get('address'),
                'date_created': date_created
            }
            
            return jsonify(customer), 201
            
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Customer name already exists'}), 400
        finally:
            conn.close()
    
    else:  # GET
        conn = get_db_connection()
        customers = conn.execute('SELECT * FROM customers ORDER BY name').fetchall()
        conn.close()
        
        return jsonify([dict(customer) for customer in customers])

@app.route('/api/customers/<customer_id>')
def get_customer(customer_id):
    """Get specific customer by ID"""
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    conn.close()
    
    if customer:
        return jsonify(dict(customer))
    return jsonify({'error': 'Customer not found'}), 404

@app.route('/api/notes', methods=['GET', 'POST'])
def notes():
    """Handle plant notes operations"""
    if request.method == 'POST':
        data = request.get_json()
        
        required_fields = ['customer_id', 'plant_name', 'condition', 'recommended_treatment', 'status']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if data['status'] not in ['healthy', 'unhealthy', 'treated']:
            return jsonify({'error': 'Invalid status. Must be healthy, unhealthy, or treated'}), 400
        
        # Verify customer exists and get customer name
        conn = get_db_connection()
        customer = conn.execute('SELECT name FROM customers WHERE id = ?', (data['customer_id'],)).fetchone()
        
        if not customer:
            conn.close()
            return jsonify({'error': 'Customer not found'}), 404
        
        note_id = str(uuid.uuid4())
        current_time = datetime.now().isoformat()
        
        conn.execute('''
            INSERT INTO plant_notes (id, customer_id, customer_name, plant_name, condition, 
                                   recommended_treatment, status, date_created, date_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (note_id, data['customer_id'], customer['name'], data['plant_name'],
              data['condition'], data['recommended_treatment'], data['status'],
              current_time, current_time))
        
        conn.commit()
        conn.close()
        
        note = {
            'id': note_id,
            'customer_id': data['customer_id'],
            'customer_name': customer['name'],
            'plant_name': data['plant_name'],
            'condition': data['condition'],
            'recommended_treatment': data['recommended_treatment'],
            'status': data['status'],
            'date_created': current_time,
            'date_updated': current_time
        }
        
        return jsonify(note), 201
    
    else:  # GET
        customer_id = request.args.get('customer_id')
        status = request.args.get('status')
        
        conn = get_db_connection()
        
        if customer_id and status:
            # Get notes for specific customer with specific status
            notes = conn.execute('''
                SELECT * FROM plant_notes 
                WHERE customer_id = ? AND status = ? 
                ORDER BY date_created DESC
            ''', (customer_id, status)).fetchall()
        elif customer_id:
            # Get all notes for specific customer
            notes = conn.execute('''
                SELECT * FROM plant_notes 
                WHERE customer_id = ? 
                ORDER BY date_created DESC
            ''', (customer_id,)).fetchall()
        else:
            # Get all notes
            notes = conn.execute('''
                SELECT * FROM plant_notes 
                ORDER BY date_created DESC
            ''').fetchall()
        
        conn.close()
        return jsonify([dict(note) for note in notes])

@app.route('/api/notes/<note_id>', methods=['GET', 'PUT', 'DELETE'])
def note_detail(note_id):
    """Handle individual note operations"""
    conn = get_db_connection()
    
    if request.method == 'GET':
        note = conn.execute('SELECT * FROM plant_notes WHERE id = ?', (note_id,)).fetchone()
        conn.close()
        
        if note:
            return jsonify(dict(note))
        return jsonify({'error': 'Note not found'}), 404
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        if not data:
            conn.close()
            return jsonify({'error': 'No data provided'}), 400
        
        if 'status' in data and data['status'] not in ['healthy', 'unhealthy', 'treated']:
            conn.close()
            return jsonify({'error': 'Invalid status'}), 400
        
        # Build update query dynamically
        update_fields = []
        values = []
        
        for field in ['plant_name', 'condition', 'recommended_treatment', 'status']:
            if field in data:
                update_fields.append(f'{field} = ?')
                values.append(data[field])
        
        if not update_fields:
            conn.close()
            return jsonify({'error': 'No valid fields to update'}), 400
        
        update_fields.append('date_updated = ?')
        values.append(datetime.now().isoformat())
        values.append(note_id)
        
        query = f'UPDATE plant_notes SET {", ".join(update_fields)} WHERE id = ?'
        
        cursor = conn.execute(query, values)
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Note not found'}), 404
        
        conn.commit()
        
        # Return updated note
        updated_note = conn.execute('SELECT * FROM plant_notes WHERE id = ?', (note_id,)).fetchone()
        conn.close()
        
        return jsonify(dict(updated_note))
    
    elif request.method == 'DELETE':
        cursor = conn.execute('DELETE FROM plant_notes WHERE id = ?', (note_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Note not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Note deleted successfully'})

@app.route('/api/customers/<customer_id>/notes')
def customer_notes(customer_id):
    """Get all notes for a specific customer"""
    status = request.args.get('status')
    
    conn = get_db_connection()
    
    # Verify customer exists
    customer = conn.execute('SELECT name FROM customers WHERE id = ?', (customer_id,)).fetchone()
    if not customer:
        conn.close()
        return jsonify({'error': 'Customer not found'}), 404
    
    if status:
        if status not in ['healthy', 'unhealthy', 'treated']:
            conn.close()
            return jsonify({'error': 'Invalid status'}), 400
        
        notes = conn.execute('''
            SELECT * FROM plant_notes 
            WHERE customer_id = ? AND status = ? 
            ORDER BY date_created DESC
        ''', (customer_id, status)).fetchall()
    else:
        notes = conn.execute('''
            SELECT * FROM plant_notes 
            WHERE customer_id = ? 
            ORDER BY date_created DESC
        ''', (customer_id,)).fetchall()
    
    conn.close()
    
    return jsonify({
        'customer_name': customer['name'],
        'notes': [dict(note) for note in notes]
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Plant Care Notes Flask Application')
    parser.add_argument('--port', '-p', type=int, default=5000, 
                       help='Port to run the Flask application on (default: 5000)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Host to bind the Flask application to (default: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true',
                       help='Run Flask in debug mode')
    return parser.parse_args()

if __name__ == '__main__':
    # Parse command line arguments
    args = parse_arguments()
    
    # Initialize database on startup
    init_db()
    
    print(f"Starting Flask application on http://{args.host}:{args.port}")
    if args.debug:
        print("Debug mode enabled")
    
    # Run the application with parsed arguments
    app.run(debug=args.debug, host=args.host, port=args.port)