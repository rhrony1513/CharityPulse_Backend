import os
from flask import Blueprint, request, jsonify, abort, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user, login_required
from models import db, User, Donation, DonationImage, Comment
from datetime import datetime
from werkzeug.utils import secure_filename

api_bp = Blueprint('api', __name__)

# Helper function for allowed file types
def allowed_file(filename):
    from config import Config
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# ------------------------
# User Registration
# ------------------------
@api_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    age = data.get('age')
    phone = data.get('phone')
    date_of_birth = data.get('date_of_birth')

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'User already exists'}), 400

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    user = User(name=name, email=email, password=hashed_password,
                age=age, phone=phone, date_of_birth=date_of_birth)
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201

# ------------------------
# User Login
# ------------------------
@api_bp.route('/login', methods=['POST'])
def login():
    data = request.form
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({'message': 'Invalid credentials'}), 401
    login_user(user)
    return jsonify({'message': 'Logged in successfully'}), 200

# ------------------------
# User Logout
# ------------------------
@api_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200

# ------------------------
# Post a Donation
# ------------------------
@api_bp.route('/donations', methods=['POST'])
@login_required
def post_donation():
    data = request.form
    title = data.get('title')
    description = data.get('description')
    location = data.get('location')
    condition = data.get('condition')
    category = data.get('category')
    
    donation = Donation(user_id=current_user.id, title=title, description=description,
                        location=location, condition=condition, category=category)
    db.session.add(donation)
    db.session.commit()
    
    # Handle file uploads (up to 5 images)
    files = request.files.getlist("images")
    for file in files[:5]:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)
            donation_image = DonationImage(donation_id=donation.id, file_path=upload_path)
            db.session.add(donation_image)
    db.session.commit()
    
    return jsonify({'message': 'Donation posted successfully'}), 201

# ------------------------
# Get All Donations (Marketplace)
# ------------------------
@api_bp.route('/donations', methods=['GET'])
def get_donations():
    donations = Donation.query.all()
    output = []
    for donation in donations:
        donation_data = {
            'id': donation.id,
            'title': donation.title,
            'description': donation.description,
            'location': donation.location,
            'condition': donation.condition,
            'category': donation.category,
            'timestamp': donation.timestamp,
            'donator': {
                'id': donation.user.id,
                'name': donation.user.name,
                'profile_picture': donation.user.profile_picture
            },
            'images': [img.file_path for img in donation.images]
        }
        output.append(donation_data)
    return jsonify(output)

# ------------------------
# Get Donation Details (with Comments)
# ------------------------
@api_bp.route('/donations/<int:donation_id>', methods=['GET'])
def donation_details(donation_id):
    donation = Donation.query.get_or_404(donation_id)
    donation_data = {
        'id': donation.id,
        'title': donation.title,
        'description': donation.description,
        'location': donation.location,
        'condition': donation.condition,
        'category': donation.category,
        'timestamp': donation.timestamp,
        'donator': {
            'id': donation.user.id,
            'name': donation.user.name,
            'email': donation.user.email,
            'profile_picture': donation.user.profile_picture
        },
        'images': [img.file_path for img in donation.images],
        'comments': []
    }
    
    for comment in donation.comments:
        comment_data = {
            'id': comment.id,
            'user_id': comment.user_id,
            'user_name': comment.user.name,
            'comment_text': comment.comment_text,
            'parent_comment_id': comment.parent_comment_id,
            'timestamp': comment.timestamp
        }
        donation_data['comments'].append(comment_data)
    
    return jsonify(donation_data)

# ------------------------
# Add a Comment / Reply
# ------------------------
@api_bp.route('/donations/<int:donation_id>/comments', methods=['POST'])
@login_required
def add_comment(donation_id):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400
    comment_text = data.get('comment_text')
    parent_comment_id = data.get('parent_comment_id')
    comment = Comment(donation_id=donation_id, user_id=current_user.id,
                      comment_text=comment_text, parent_comment_id=parent_comment_id)
    db.session.add(comment)
    db.session.commit()
    return jsonify({'message': 'Comment added successfully'}), 201

# ------------------------
# Get Current User's Profile
# ------------------------
@api_bp.route('/profile', methods=['GET'])
@login_required
def profile():
    user = current_user
    donations = Donation.query.filter_by(user_id=user.id).all()
    donations_data = []
    for donation in donations:
        donation_data = {
            'id': donation.id,
            'title': donation.title,
            'description': donation.description,
            'location': donation.location,
            'condition': donation.condition,
            'category': donation.category,
            'timestamp': donation.timestamp,
            'images': [img.file_path for img in donation.images]
        }
        donations_data.append(donation_data)
    profile_data = {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'age': user.age,
        'phone': user.phone,
        'date_of_birth': user.date_of_birth,
        'profile_picture': user.profile_picture,
        'donations': donations_data
    }
    return jsonify(profile_data)
