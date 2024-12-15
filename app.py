from flask import Flask, render_template, request, jsonify
import sqlite3
import logging
from datetime import datetime
import os
import pandas as pd
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, text

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db_path = os.path.join(os.getcwd(), 'data.db')
db_engine = create_engine(f"sqlite:///{db_path}")

table_mapping = {
    "keylogs": ["application", "time", "time_dt", "text", "package_id"],
    "sms_messages": ["sms_type", "time", "time_dt", "from_to", "text", "location_id", "contact_id"],
    "chat_messages": ["messenger", "time", "time_dt", "sender", "text", "contact_id"],
    "contacts": ["name", "phone_number", "email_id", "last_contacted", "last_contacted_dt"],
    "calls": ["call_type", "time", "time_dt", "from_to", "duration", "location_id", "contact_id"],
    "installedapps": ["application_name", "package_name", "installed_date"],
    "locations": ["location_text"]
}

def get_db_connection():
    try:
        conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_datetime(timestamp):
    try:
        if isinstance(timestamp, str):
            dt_object = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        else:
            dt_object = datetime.fromtimestamp(timestamp)
        return dt_object.strftime("%b %d, %I:%M %p")
    except (ValueError, TypeError) as e:
        logging.error(f"Error formatting timestamp {timestamp}: {str(e)}")
        return str(timestamp)

def get_columns(conn, table):
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return [row['name'] for row in cursor]

def _parse_and_insert(conn, table, data, columns):
    placeholders = ', '.join(['?' for _ in columns])
    query = f'INSERT OR IGNORE INTO {table} ({", ".join(columns)}) VALUES ({placeholders})'
    conn.execute(query, data)
    return conn.execute(f'SELECT last_insert_rowid()').fetchone()[0]

def parse_and_insert_contact(conn, name, phone_number, email_id):
    try:
        contact = conn.execute('SELECT contact_id from contacts WHERE name = ?', (name,)).fetchone()
        if contact:
            return contact[0]

        data = (name, phone_number, email_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        columns = ["name","phone_number","email_id", "last_contacted", "last_contacted_dt"]
        return _parse_and_insert(conn, "contacts", data, columns)
    except Exception as e:
        logging.error(f"Error Inserting Contact: {e}")
        return None

def get_or_create_location(location_text, db_engine):
    """Retrieves a location_id from the locations table or creates a new entry if the location does not exist.
    Args:
        location_text (str): The text of the location.
        db_engine (sqlalchemy.engine.Engine): The SQLAlchemy database engine.

    Returns:
        int: The location ID.
    """

    if pd.isna(location_text):
       return None
    with db_engine.connect() as conn:
      query = text("SELECT location_id FROM locations WHERE location_text = :location_text")
      result = conn.execute(query, {"location_text": location_text}).fetchone()
      if result:
          return result[0]
      else:
        insert_query = text("INSERT INTO locations (location_text) VALUES (:location_text)")
        result = conn.execute(insert_query, {"location_text": location_text})
        conn.commit()
        return result.lastrowid

def load_and_clean_data(file_path, db_engine, table_mapping):
    """
    Loads data from a CSV or Excel file, performs basic cleaning, and inserts into the appropriate table based on column names.
    Args:
        file_path (str): The path to the CSV or Excel file.
        db_engine (sqlalchemy.engine.Engine): The SQLAlchemy database engine.
    Returns:
        None: The function inserts data into the database.
    """
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path)  # Use pandas read_excel for XLSX files
        else:
            raise ValueError("Unsupported file type. Only CSV and XLSX are allowed.")

        # Convert all column names to lowercase and replace spaces with underscores
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]

        # Basic cleaning : Remove leading and trailing whitespace
        for col in df.columns:
            if df[col].dtype == 'object': #check if column contains strings
                 df[col] = df[col].str.strip()

        # Identify the target table based on column names
        target_table = None
        for table_name, expected_columns in table_mapping.items():
            if set(expected_columns).issubset(df.columns):
              target_table = table_name
              break
        if not target_table:
              print(f"Error: Could not identify target table for columns: {list(df.columns)}")
              return

        print(f"Loading data into table: {target_table}")

        # Perform specific transformations based on table
        if target_table == "keylogs":
            df = transform_keylogs(df)
        elif target_table == "sms_messages":
             df = transform_sms_messages(df, db_engine)
        elif target_table == "chat_messages":
            df = transform_chat_messages(df,db_engine)
        elif target_table == "contacts":
            df = transform_contacts(df)
        elif target_table == "calls":
           df = transform_calls(df, db_engine)
        elif target_table == "installedapps":
           df = transform_installedapps(df)
        elif target_table == "locations":
            df = transform_locations(df)
        else:
            print(f"Error: No specific transformations defined for table: {target_table}")
            return

        # Detect and Remove Duplicates
        original_length = len(df)
        df = df.drop_duplicates()
        duplicates_removed = original_length - len(df)
        if duplicates_removed > 0:
            print(f"Removed {duplicates_removed} duplicate rows from {target_table}")

        # Insert data into the database
        df.to_sql(target_table, db_engine, if_exists='append', index=False)
        print(f"Successfully loaded data into {target_table}")

        # Save the file name (you can still save as CSV if you prefer)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(UPLOAD_FOLDER, "cleaned_output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        filename = os.path.basename(file_path)
        base_name, _ = os.path.splitext(filename)
        output_file = os.path.join(output_dir, f"{base_name}_cleaned_{timestamp}.csv")
        df.to_csv(output_file, index=False)

    except Exception as e:
        print(f"Error loading data from {file_path}: {e}")

def transform_keylogs(df):
   df['time_dt'] = pd.to_datetime(df['time'], format='%b %d, %I:%M %p', errors='coerce')
   return df

def transform_sms_messages(df, db_engine):
    """Transforms SMS message data by parsing time, resolving location and contact IDs."""
    df['time_dt'] = pd.to_datetime(df['time'], format='%b %d, %I:%M %p', errors='coerce')

    with db_engine.connect() as conn:
      # Handle missing contact and location ids
      if 'name' in df.columns:
          df['contact_id'] = df.apply(lambda row: parse_and_insert_contact(conn, row['name'], row['from_to'], row['email_id']), axis=1)
      elif 'from_to' in df.columns:
          df['contact_id'] = df['from_to'].apply(lambda x: parse_and_insert_contact(conn, x, x, x))
      df['location_id'] = df['location'].apply(lambda x: get_or_create_location(x, db_engine))
      df = df.drop(columns = ['location'])
      return df

def transform_chat_messages(df, db_engine):
    """Transforms chat message data by parsing time and resolving contact IDs."""
    df['time_dt'] = pd.to_datetime(df['time'], format='%b %d, %I:%M %p', errors='coerce')
    with db_engine.connect() as conn:
        df['contact_id'] = df['sender'].apply(lambda x: parse_and_insert_contact(conn, x, x, x))
    return df

def transform_contacts(df):
    """Transforms contact data by parsing last_contacted time."""
    df['last_contacted_dt'] = pd.to_datetime(df['last_contacted'], format='%b %d, %I:%M %p', errors='coerce')
    return df

def transform_calls(df, db_engine):
    """Transforms call data by parsing time, duration and resolving location and contact IDs."""
    df['time_dt'] = pd.to_datetime(df['time'], format='%b %d, %I:%M %p', errors='coerce')
    df['duration'] = df['duration_(sec)'].str.replace(r'[^\d]', '', regex=True).fillna(0).astype(int)
    df = df.drop(columns=['duration_(sec)'])

    with db_engine.connect() as conn:
      # Handle missing contact and location ids
      if 'name' in df.columns:
          df['contact_id'] = df.apply(lambda row: parse_and_insert_contact(conn, row['name'], row['from_to'], row['email_id']), axis=1)
      elif 'from_to' in df.columns:
          df['contact_id'] = df['from_to'].apply(lambda x: parse_and_insert_contact(conn, x, x, x))
      df['location_id'] = df['location'].apply(lambda x: get_or_create_location(x, db_engine))
      df = df.drop(columns = ['location'])
      return df

def transform_installedapps(df):
    """Transforms installed app data by parsing installed date."""
    df['installed_date'] = pd.to_datetime(df['installed_date'], format='%b %d, %I:%M %p', errors='coerce')
    return df

def transform_locations(df):
    return df

# Routes for serving HTML pages:
@app.route('/')
def index():
    return render_template('base.html')

# API route to handle file uploads
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        try:
            with db_engine.connect() as conn:
                load_and_clean_data(file_path, conn, table_mapping)
            return jsonify({'message': 'File uploaded and data processed successfully'}), 200
        except Exception as e:
            logging.error(f"Error processing data from {file_path}: {e}")
            return jsonify({'error': 'Failed to process data', 'message': str(e)}), 500
    else:
        return jsonify({'error': 'File type not allowed'}), 400

# Routes for fetching data (used by app.js):

@app.route('/get_chats', methods=['GET'])
def get_chats():
    conn = get_db_connection()
    if conn:
        try:
            chats = conn.execute('''
                SELECT 
                    c.name,
                    (SELECT text FROM chat_messages WHERE sender = c.name ORDER BY time_dt DESC LIMIT 1) as last_message,
                    (SELECT time_dt FROM chat_messages WHERE sender = c.name ORDER BY time_dt DESC LIMIT 1) as time
                FROM (SELECT DISTINCT sender as name FROM chat_messages) c
                ORDER BY time DESC
            ''').fetchall()
            return jsonify([dict(row) for row in chats])
        except Exception as e:
            logging.error(f"Error fetching chats: {e}")
            return jsonify({'error': 'Failed to fetch chats'}), 500
        finally:
            conn.close()
    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/get_calls', methods=['GET'])
def get_calls():
    conn = get_db_connection()
    if conn:
         try:
            calls = conn.execute('''
                SELECT 
                    c.from_to,
                    c.call_type,
                    c.time_dt AS time,
                    c.duration
                FROM calls c
                ORDER BY time_dt DESC
            ''').fetchall()
            return jsonify([dict(row) for row in calls])
         except Exception as e:
            logging.error(f"Error fetching calls: {e}")
            return jsonify({'error': 'Failed to fetch calls'}), 500
         finally:
            conn.close()
    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/get_keylogs', methods=['GET'])
def get_keylogs():
    conn = get_db_connection()
    if conn:
        try:
            keylogs = conn.execute('SELECT * FROM keylogs ORDER BY time_dt DESC').fetchall()
            return jsonify([dict(row) for row in keylogs])
        except Exception as e:
            logging.error(f"Error fetching keylogs: {e}")
            return jsonify({'error': 'Failed to fetch keylogs'}), 500
        finally:
            conn.close()
    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/get_contacts', methods=['GET'])
def get_contacts():
    conn = get_db_connection()
    if conn:
        try:
            contacts = conn.execute('SELECT * FROM contacts ORDER BY name').fetchall()
            return jsonify([dict(row) for row in contacts])
        except Exception as e:
            logging.error(f"Error fetching contacts: {e}")
            return jsonify({'error': 'Failed to fetch contacts'}), 500
        finally:
            conn.close()
    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/get_sms', methods=['GET'])
def get_sms():
    conn = get_db_connection()
    if conn:
        try:
            sms = conn.execute('''
                SELECT 
                    from_to,
                    text,
                    time_dt as time
                FROM sms_messages
                ORDER BY time_dt DESC
            ''').fetchall()
            return jsonify([dict(row) for row in sms])
        except Exception as e:
            logging.error(f"Error fetching SMS: {e}")
            return jsonify({'error': 'Failed to fetch SMS'}), 500
        finally:
            conn.close()
    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/get_installed_apps', methods=['GET'])
def get_installed_apps():
    conn = get_db_connection()
    if conn:
        try:
            apps = conn.execute('SELECT * FROM installedApps ORDER BY application_name').fetchall()
            return jsonify([dict(row) for row in apps])
        except Exception as e:
            logging.error(f"Error fetching installed apps: {e}")
            return jsonify({'error': 'Failed to fetch installed apps'}), 500
        finally:
            conn.close()
    return jsonify({'error': 'Database connection failed'}), 500

# Routes for handling search:

@app.route('/search_chats', methods=['POST'])
def search_chats():
    return search_data('chat_messages', ['sender', 'text'])

@app.route('/search_calls', methods=['POST'])
def search_calls():
    return search_data('calls', ['from_to', 'call_type'])

@app.route('/search_keylogs', methods=['POST'])
def search_keylogs():
    return search_data('keylogs', ['application', 'text'])

@app.route('/search_contacts', methods=['POST'])
def search_contacts():
    return search_data('contacts', ['name', 'phone_number', 'email_id'])

@app.route('/search_sms', methods=['POST'])
def search_sms():
    return search_data('sms_messages', ['from_to', 'text'])

@app.route('/search_apps', methods=['POST'])
def search_apps():
    return search_data('installedApps', ['application_name', 'package_name'])

def search_data(table, columns):
    search_term = request.form.get('search_term')
    if not search_term:
        return jsonify([])

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        query = f'''
            SELECT *
            FROM {table}
            WHERE {' OR '.join(f"{col} LIKE ?" for col in columns)}
            ORDER BY {'time_dt DESC' if 'time_dt' in get_columns(conn, table) else 'name'}
            LIMIT 50
        '''
        results = conn.execute(query, [f'%{search_term}%'] * len(columns)).fetchall()
        return jsonify([dict(row) for row in results])
    except Exception as e:
        logging.error(f"Search error in table {table}: {e}")
        return jsonify({'error': 'Search failed'}), 500
    finally:
        conn.close()

# Route for individual chat messages
@app.route('/chat/<name>')
def chat(name):
     conn = get_db_connection()
     if conn:
         try:
              messages = conn.execute('''
                SELECT *
                FROM chat_messages
                WHERE sender = ? OR sender = 'You'
                ORDER BY time_dt
            ''', (name,)).fetchall()
              return jsonify([dict(row) for row in messages])
         except Exception as e:
             logging.error(f"Error fetching chat messages for {name}: {e}")
             return jsonify({'error': 'Failed to fetch chat messages'}), 500
         finally:
             conn.close()
     return jsonify({'error': 'Database connection failed'}), 500

# Route for individual SMS messages
@app.route('/sms/<name>')
def sms_messages(name):
   conn = get_db_connection()
   if conn:
        try:
            messages = conn.execute('''
                SELECT *
                FROM sms_messages
                WHERE from_to = ?
                ORDER BY time_dt DESC
            ''', (name,)).fetchall()
            return jsonify([dict(row) for row in messages])
        except Exception as e:
            logging.error(f"Error fetching SMS messages for {name}: {e}")
            return jsonify({'error': 'Failed to fetch SMS messages'}), 500
        finally:
            conn.close()
   return jsonify({'error': 'Database connection failed'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)