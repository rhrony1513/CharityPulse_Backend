import os
from flask import Flask, send_from_directory, abort, jsonify
from config import Config
from models import db
from flask_login import LoginManager
from flask_cors import CORS

# Correct relative path to the build folder
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend/build'))

app = Flask(__name__, static_folder=frontend_dir, static_url_path='/')
app.config.from_object(Config)

# Enable CORS
CORS(app, origins=["http://localhost:3000"])

# Init DB & Login
db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'api.login'
login_manager.init_app(app)

from models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'message': 'Unauthorized access'}), 401

# Import your API routes
from routes import api_bp
app.register_blueprint(api_bp, url_prefix='/api')

# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(os.path.join(app.root_path, 'static/uploads'), filename)

# Serve React app
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    if path.startswith('api'):
        return abort(404)

    file_path = os.path.join(frontend_dir, path)
    if path != "" and os.path.exists(file_path):
        return send_from_directory(frontend_dir, path)
    else:
        return send_from_directory(frontend_dir, 'index.html')

if __name__ == '__main__':
    app.run(debug=True)
