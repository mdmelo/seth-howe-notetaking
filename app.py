from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
import sqlite3
import uuid
from datetime import datetime
import os
import argparse
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from werkzeug.utils import secure_filename
from PIL import Image
import shutil

app = Flask(__name__)

# Configuration
DATABASE = 'plant_notes.db'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_customer_upload_path(customer_id):
    """Get the upload path for a specific customer"""
    path = os.path.join(UPLOAD_FOLDER, customer_id)
    os.makedirs(path, exist_ok=True)
    return path

def get_note_upload_path(customer_id, note_id):
    """Get the upload path for a specific note"""
    path = os.path.join(UPLOAD_FOLDER, customer_id, note_id)
    os.makedirs(path, exist_ok=True)
    return path

def resize_image(image_path, max_width=1200, max_height=1200, quality=85):
    """Resize image to reduce file size while maintaining quality"""
    try:
        with Image.open(image_path) as img:
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Calculate new dimensions
            width, height = img.size
            if width > max_width or height > max_height:
                ratio = min(max_width/width, max_height/height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save with optimization
            img.save(image_path, optimize=True, quality=quality)
            return True
    except Exception as e:
        print(f"Error resizing image {image_path}: {str(e)}")
        return False

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
    
    # Create note_images table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS note_images (
            id TEXT PRIMARY KEY,
            note_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            date_uploaded TEXT NOT NULL,
            FOREIGN KEY (note_id) REFERENCES plant_notes (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/uploads/<customer_id>/<note_id>/<filename>')
def uploaded_file(customer_id, note_id, filename):
    """Serve uploaded images"""
    try:
        # Security check - ensure the file exists in our database
        conn = get_db_connection()
        image = conn.execute('''
            SELECT file_path FROM note_images 
            WHERE filename = ? AND note_id = ?
        ''', (filename, note_id)).fetchone()
        conn.close()
        
        if not image:
            return jsonify({'error': 'Image not found'}), 404
        
        # Serve the file
        directory = os.path.join(UPLOAD_FOLDER, customer_id, note_id)
        return send_from_directory(directory, filename)
    except Exception as e:
        print(f"Error serving file: {str(e)}")
        return jsonify({'error': 'Error serving file'}), 500

@app.route('/api/notes/<note_id>/images', methods=['POST', 'DELETE'])
def note_images(note_id):
    """Handle image operations for existing notes"""
    if request.method == 'POST':
        # Add images to existing note
        files = request.files.getlist('images')
        
        if not files or not any(file.filename for file in files):
            return jsonify({'error': 'No images provided'}), 400
        
        conn = get_db_connection()
        
        # Verify note exists and get customer info
        note = conn.execute('SELECT customer_id FROM plant_notes WHERE id = ?', (note_id,)).fetchone()
        if not note:
            conn.close()
            return jsonify({'error': 'Note not found'}), 404
        
        try:
            uploaded_images = []
            upload_path = get_note_upload_path(note['customer_id'], note_id)
            current_time = datetime.now().isoformat()
            
            for file in files:
                if file and file.filename and allowed_file(file.filename):
                    # Generate unique filename
                    file_extension = file.filename.rsplit('.', 1)[1].lower()
                    unique_filename = f"{uuid.uuid4()}.{file_extension}"
                    file_path = os.path.join(upload_path, unique_filename)
                    
                    # Save file
                    file.save(file_path)
                    
                    # Resize image to reduce file size
                    resize_image(file_path)
                    
                    # Get file size
                    file_size = os.path.getsize(file_path)
                    
                    # Store image info in database
                    image_id = str(uuid.uuid4())
                    conn.execute('''
                        INSERT INTO note_images (id, note_id, filename, original_filename, 
                                               file_path, file_size, date_uploaded)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (image_id, note_id, unique_filename, file.filename,
                          file_path, file_size, current_time))
                    
                    uploaded_images.append({
                        'id': image_id,
                        'filename': unique_filename,
                        'original_filename': file.filename,
                        'url': f"/uploads/{note['customer_id']}/{note_id}/{unique_filename}"
                    })
            
            # Update note's date_updated
            conn.execute('UPDATE plant_notes SET date_updated = ? WHERE id = ?', 
                        (current_time, note_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'message': f'{len(uploaded_images)} images uploaded successfully',
                'images': uploaded_images
            }), 201
            
        except Exception as e:
            conn.close()
            print(f"Error uploading images: {str(e)}")
            return jsonify({'error': 'Failed to upload images'}), 500
    
    elif request.method == 'DELETE':
        # Delete specific image
        image_id = request.json.get('image_id') if request.json else None
        
        if not image_id:
            return jsonify({'error': 'Image ID required'}), 400
        
        conn = get_db_connection()
        
        # Get image info
        image = conn.execute('''
            SELECT file_path FROM note_images WHERE id = ? AND note_id = ?
        ''', (image_id, note_id)).fetchone()
        
        if not image:
            conn.close()
            return jsonify({'error': 'Image not found'}), 404
        
        try:
            # Delete from database
            conn.execute('DELETE FROM note_images WHERE id = ?', (image_id,))
            
            # Update note's date_updated
            current_time = datetime.now().isoformat()
            conn.execute('UPDATE plant_notes SET date_updated = ? WHERE id = ?', 
                        (current_time, note_id))
            
            conn.commit()
            conn.close()
            
            # Delete file from filesystem
            try:
                if os.path.exists(image['file_path']):
                    os.remove(image['file_path'])
            except Exception as e:
                print(f"Error deleting file {image['file_path']}: {str(e)}")
            
            return jsonify({'message': 'Image deleted successfully'})
            
        except Exception as e:
            conn.close()
            print(f"Error deleting image: {str(e)}")
            return jsonify({'error': 'Failed to delete image'}), 500

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
        # Handle multipart form data for file uploads
        if 'application/json' in request.content_type:
            data = request.get_json()
            files = []
        else:
            # Handle form data with files
            data = {
                'customer_id': request.form.get('customer_id'),
                'plant_name': request.form.get('plant_name'),
                'condition': request.form.get('condition'),
                'recommended_treatment': request.form.get('recommended_treatment'),
                'status': request.form.get('status')
            }
            files = request.files.getlist('images')
        
        required_fields = ['customer_id', 'plant_name', 'condition', 'recommended_treatment', 'status']
        if not data or not all(field in data and data[field] for field in required_fields):
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
        
        try:
            # Insert the note
            conn.execute('''
                INSERT INTO plant_notes (id, customer_id, customer_name, plant_name, condition, 
                                       recommended_treatment, status, date_created, date_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (note_id, data['customer_id'], customer['name'], data['plant_name'],
                  data['condition'], data['recommended_treatment'], data['status'],
                  current_time, current_time))
            
            # Handle file uploads
            uploaded_images = []
            if files:
                upload_path = get_note_upload_path(data['customer_id'], note_id)
                
                for file in files:
                    if file and file.filename and allowed_file(file.filename):
                        # Generate unique filename
                        file_extension = file.filename.rsplit('.', 1)[1].lower()
                        unique_filename = f"{uuid.uuid4()}.{file_extension}"
                        file_path = os.path.join(upload_path, unique_filename)
                        
                        # Save file
                        file.save(file_path)
                        
                        # Resize image to reduce file size
                        resize_image(file_path)
                        
                        # Get file size
                        file_size = os.path.getsize(file_path)
                        
                        # Store image info in database
                        image_id = str(uuid.uuid4())
                        conn.execute('''
                            INSERT INTO note_images (id, note_id, filename, original_filename, 
                                                   file_path, file_size, date_uploaded)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (image_id, note_id, unique_filename, file.filename,
                              file_path, file_size, current_time))
                        
                        uploaded_images.append({
                            'id': image_id,
                            'filename': unique_filename,
                            'original_filename': file.filename,
                            'url': f"/uploads/{data['customer_id']}/{note_id}/{unique_filename}"
                        })
            
            conn.commit()
            
            note = {
                'id': note_id,
                'customer_id': data['customer_id'],
                'customer_name': customer['name'],
                'plant_name': data['plant_name'],
                'condition': data['condition'],
                'recommended_treatment': data['recommended_treatment'],
                'status': data['status'],
                'date_created': current_time,
                'date_updated': current_time,
                'images': uploaded_images
            }
            
            return jsonify(note), 201
            
        except Exception as e:
            # Cleanup uploaded files if database insert fails
            if 'upload_path' in locals():
                try:
                    shutil.rmtree(upload_path)
                except:
                    pass
            print(f"Error creating note: {str(e)}")
            return jsonify({'error': 'Failed to create note'}), 500
        finally:
            conn.close()
    
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
        
        # Get images for each note
        notes_with_images = []
        for note in notes:
            note_dict = dict(note)
            
            # Get images for this note
            images = conn.execute('''
                SELECT id, filename, original_filename FROM note_images 
                WHERE note_id = ? ORDER BY date_uploaded
            ''', (note['id'],)).fetchall()
            
            note_dict['images'] = [
                {
                    'id': img['id'],
                    'filename': img['filename'],
                    'original_filename': img['original_filename'],
                    'url': f"/uploads/{note['customer_id']}/{note['id']}/{img['filename']}"
                }
                for img in images
            ]
            
            notes_with_images.append(note_dict)
        
        conn.close()
        return jsonify(notes_with_images)

@app.route('/api/notes/<note_id>', methods=['GET', 'PUT', 'DELETE'])
def note_detail(note_id):
    """Handle individual note operations"""
    conn = get_db_connection()
    
    if request.method == 'GET':
        note = conn.execute('SELECT * FROM plant_notes WHERE id = ?', (note_id,)).fetchone()
        
        if not note:
            conn.close()
            return jsonify({'error': 'Note not found'}), 404
        
        # Get images for this note
        images = conn.execute('''
            SELECT id, filename, original_filename FROM note_images 
            WHERE note_id = ? ORDER BY date_uploaded
        ''', (note_id,)).fetchall()
        
        note_dict = dict(note)
        note_dict['images'] = [
            {
                'id': img['id'],
                'filename': img['filename'],
                'original_filename': img['original_filename'],
                'url': f"/uploads/{note['customer_id']}/{note['id']}/{img['filename']}"
            }
            for img in images
        ]
        
        conn.close()
        return jsonify(note_dict)
    
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
        
        # Return updated note with images
        updated_note = conn.execute('SELECT * FROM plant_notes WHERE id = ?', (note_id,)).fetchone()
        
        # Get images for this note
        images = conn.execute('''
            SELECT id, filename, original_filename FROM note_images 
            WHERE note_id = ? ORDER BY date_uploaded
        ''', (note_id,)).fetchall()
        
        note_dict = dict(updated_note)
        note_dict['images'] = [
            {
                'id': img['id'],
                'filename': img['filename'],
                'original_filename': img['original_filename'],
                'url': f"/uploads/{updated_note['customer_id']}/{updated_note['id']}/{img['filename']}"
            }
            for img in images
        ]
        
        conn.close()
        return jsonify(note_dict)
    
    elif request.method == 'DELETE':
        # Get note info first to clean up files
        note = conn.execute('SELECT customer_id FROM plant_notes WHERE id = ?', (note_id,)).fetchone()
        
        if not note:
            conn.close()
            return jsonify({'error': 'Note not found'}), 404
        
        # Delete the note (images will be deleted via CASCADE)
        cursor = conn.execute('DELETE FROM plant_notes WHERE id = ?', (note_id,))
        conn.commit()
        conn.close()
        
        # Clean up uploaded files
        try:
            upload_path = os.path.join(UPLOAD_FOLDER, note['customer_id'], note_id)
            if os.path.exists(upload_path):
                shutil.rmtree(upload_path)
        except Exception as e:
            print(f"Error cleaning up files for note {note_id}: {str(e)}")
        
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
    
    # Get images for each note
    notes_with_images = []
    for note in notes:
        note_dict = dict(note)
        
        # Get images for this note
        images = conn.execute('''
            SELECT id, filename, original_filename FROM note_images 
            WHERE note_id = ? ORDER BY date_uploaded
        ''', (note['id'],)).fetchall()
        
        note_dict['images'] = [
            {
                'id': img['id'],
                'filename': img['filename'],
                'original_filename': img['original_filename'],
                'url': f"/uploads/{note['customer_id']}/{note['id']}/{img['filename']}"
            }
            for img in images
        ]
        
        notes_with_images.append(note_dict)
    
    conn.close()
    
    return jsonify({
        'customer_name': customer['name'],
        'notes': notes_with_images
    })

@app.route('/api/customers/<customer_id>/report')
def generate_customer_report(customer_id):
    """Generate PDF report for a specific customer"""
    try:
        conn = get_db_connection()
        
        # Get customer information
        customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
        if not customer:
            conn.close()
            return jsonify({'error': 'Customer not found'}), 404
        
        # Get all notes for the customer
        notes = conn.execute('''
            SELECT * FROM plant_notes 
            WHERE customer_id = ? 
            ORDER BY date_created DESC
        ''', (customer_id,)).fetchall()
        
        conn.close()
        
        # Generate PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, 
                              topMargin=72, bottomMargin=18)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2563eb')
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#1f2937')
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            textColor=colors.HexColor('#374151')
        )
        
        # Title
        title = Paragraph("Plant Care Report", title_style)
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Customer Information
        customer_heading = Paragraph("Customer Information", heading_style)
        elements.append(customer_heading)
        
        customer_data = [
            ['Name:', customer['name']],
            ['Email:', customer['email'] or 'Not provided'],
            ['Phone:', customer['phone'] or 'Not provided'],
            ['Address:', customer['address'] or 'Not provided'],
            ['Customer Since:', datetime.fromisoformat(customer['date_created']).strftime('%B %d, %Y')]
        ]
        
        customer_table = Table(customer_data, colWidths=[1.5*inch, 4*inch])
        customer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(customer_table)
        elements.append(Spacer(1, 30))
        
        # Plant Care Notes
        notes_heading = Paragraph("Plant Care Notes", heading_style)
        elements.append(notes_heading)
        
        if not notes:
            no_notes = Paragraph("No plant care notes found for this customer.", normal_style)
            elements.append(no_notes)
        else:
            # Summary statistics
            total_notes = len(notes)
            healthy_count = sum(1 for note in notes if note['status'] == 'healthy')
            unhealthy_count = sum(1 for note in notes if note['status'] == 'unhealthy')
            treated_count = sum(1 for note in notes if note['status'] == 'treated')
            
            summary_text = f"Total Plants: {total_notes} | Healthy: {healthy_count} | Unhealthy: {unhealthy_count} | Treated: {treated_count}"
            summary = Paragraph(summary_text, normal_style)
            elements.append(summary)
            elements.append(Spacer(1, 20))
            
            # Individual notes (images are excluded from reports as requested)
            for i, note in enumerate(notes):
                # Note header
                note_title = f"{note['plant_name']} - {note['status'].title()}"
                note_heading = Paragraph(f"<b>{note_title}</b>", normal_style)
                elements.append(note_heading)
                
                # Note details
                note_data = [
                    ['Date:', datetime.fromisoformat(note['date_created']).strftime('%B %d, %Y')],
                    ['Status:', note['status'].title()],
                    ['Condition:', note['condition']],
                    ['Treatment:', note['recommended_treatment']]
                ]
                
                if note['date_updated'] != note['date_created']:
                    note_data.append(['Last Updated:', datetime.fromisoformat(note['date_updated']).strftime('%B %d, %Y')])
                
                note_table = Table(note_data, colWidths=[1.2*inch, 4.3*inch])
                
                # Status-based coloring
                status_color = colors.HexColor('#10b981') if note['status'] == 'healthy' else \
                              colors.HexColor('#ef4444') if note['status'] == 'unhealthy' else \
                              colors.HexColor('#3b82f6')
                
                note_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BACKGROUND', (0, 1), (0, 1), status_color),
                    ('TEXTCOLOR', (0, 1), (0, 1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                
                elements.append(note_table)
                
                # Add space between notes
                if i < len(notes) - 1:
                    elements.append(Spacer(1, 20))
        
        # Footer
        elements.append(Spacer(1, 30))
        footer_text = f"Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        footer = Paragraph(footer_text, ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor=colors.grey
        ))
        elements.append(footer)
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create response
        response = send_file(
            BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"plant_care_report_{customer['name'].replace(' ', '_')}.pdf"
        )
        
        return response
        
    except Exception as e:
        print(f"Error generating PDF report: {str(e)}")
        return jsonify({'error': 'Failed to generate report'}), 500

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