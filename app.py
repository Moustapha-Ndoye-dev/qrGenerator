from flask import Flask, send_file, jsonify, render_template, request
import qrcode
import sqlite3
import uuid
from flask_cors import CORS
import os
import io

app = Flask(__name__)
CORS(app)  # Initialisation du CORS pour permettre les requêtes entre origines
DATABASE = 'database.db'

# Fonction d'initialisation de la base de données
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL UNIQUE,
                used BOOLEAN NOT NULL DEFAULT 0  -- Champ pour marquer si le token est utilisé
            )
        ''')
        conn.commit()

@app.route('/')
def index():
    # Affiche une page d'accueil simple
    return render_template('index.html')

@app.route('/generate_qr', methods=['GET'])
def generate_qr():
    # Génère un token unique
    token = str(uuid.uuid4())

    # Enregistre le token dans la base de données
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO tokens (token) VALUES (?)', (token,))
            conn.commit()
    except sqlite3.Error as e:
        return jsonify({"error": f"Erreur lors de l'insertion du token dans la base de données: {str(e)}"}), 500

    # Génère un code QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Sauvegarde l'image dans un objet BytesIO
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)  # Revenir au début du flux

    # Renvoi du fichier pour téléchargement
    return send_file(img_bytes, as_attachment=True, download_name=f"{token}.png", mimetype='image/png')

@app.route('/api/tokens', methods=['GET'])
def get_tokens():
    # Récupère tous les tokens non utilisés de la base de données
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT token FROM tokens WHERE used = 0')  # Filtre pour ne récupérer que les tokens non utilisés
            tokens = [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        return jsonify({"error": f"Erreur lors de la récupération des tokens: {str(e)}"}), 500
    
    return jsonify(tokens)

@app.route('/api/tokens/invalidate', methods=['POST'])
def invalidate_token():
    # Récupère le token à invalider
    token = request.json.get('token')

    if not token:
        return jsonify({"error": "Token is required"}), 400

    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            # Vérifie si le token existe et s'il n'est pas déjà utilisé
            cursor.execute('SELECT used FROM tokens WHERE token = ?', (token,))
            result = cursor.fetchone()

            if result is None:
                return jsonify({"error": "Token not found"}), 404

            if result[0] == 1:
                return jsonify({"error": "Token has already been used"}), 400

            # Marque le token comme utilisé
            cursor.execute('UPDATE tokens SET used = 1 WHERE token = ?', (token,))
            conn.commit()

        return jsonify({"message": "Token invalidated successfully"}), 200

    except sqlite3.Error as e:
        return jsonify({"error": f"Erreur lors de l'invalidation du token: {str(e)}"}), 500

if __name__ == '__main__':
    init_db()  # Initialisation de la base de données au démarrage de l'application
    port = int(os.environ.get("PORT", 8080))  # Utilisation du port spécifié par Railway ou du port 8080 par défaut
    app.run(debug=True, port=port, host='0.0.0.0')  # Permet à l'application d'écouter sur toutes les interfaces
