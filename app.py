from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import qrcode
import os
import socket
from PIL import Image
from datetime import datetime, timedelta

app = Flask(__name__)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# QR Code Directory
qr_code_dir = 'static/qr_codes'
if not os.path.exists(qr_code_dir):
    os.makedirs(qr_code_dir)

# Get Local IP Address
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)

# Database Model
class UserSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    comments = db.Column(db.Text, nullable=True)
    qr_code_path = db.Column(db.String(200), nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)  # New column for expiry dates

# Create Database Tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    unique_id = os.urandom(4).hex()
    redirect_url = f"{request.host_url}form/{unique_id}"

    # Generate QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(redirect_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Resize QR Code to 2cm x 2cm (236x236 pixels at 300 DPI)
    desired_size = (236, 236)
    img = img.resize(desired_size, Image.Resampling.LANCZOS)

    # Save QR Code
    qr_filename = f"{qr_code_dir}/{unique_id}.png"
    img.save(qr_filename)

    return render_template('qr_code.html', qr_image=qr_filename, redirect_url=redirect_url)

@app.route('/form/<unique_id>', methods=['GET', 'POST'])
def form(unique_id):
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        dob = datetime.strptime(request.form['dob'], '%Y-%m-%d').date()
        gender = request.form['gender']
        country = request.form['country']
        comments = request.form['comments']

        # Debugging Output
        print(f"Received Data: {name}, {email}, {phone}, {dob}, {gender}, {country}, {comments}")

        # Save data to the database
        submission = UserSubmission(
            name=name,
            email=email,
            phone=phone,
            dob=dob,
            gender=gender,
            country=country,
            comments=comments,
            qr_code_path=None,  # Default value
            expiry_date=None    # Default value
        )
        db.session.add(submission)
        db.session.commit()

        # Pass submission_id to the template
        return render_template(
            'success.html',
            name=name,
            email=email,
            phone=phone,
            dob=dob,
            gender=gender,
            country=country,
            comments=comments,
            submission_id=submission.id  # Pass the ID here
        )

    return render_template('form.html')


@app.route('/generate_user_qr/<int:id>')
def generate_user_qr(id):
    user = UserSubmission.query.get_or_404(id)

    # Generate QR Code with Profile URL
    qr_data = f"{request.host_url}profile/{user.id}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Resize the QR code to 236x236 pixels (2cm x 2cm at 300 DPI)
    desired_size = (236, 236)
    img = img.resize(desired_size, Image.Resampling.LANCZOS)

    # Save the QR Code with a unique filename
    qr_filename = f"{qr_code_dir}/{user.id}_id_card.png"
    img.save(qr_filename)

    # Add expiry date (30 days from today)
    user.qr_code_path = qr_filename
    user.expiry_date = datetime.utcnow().date() + timedelta(days=30)
    db.session.commit()

    return render_template(
        'user_qr.html',
        qr_image=url_for('static', filename=f'qr_codes/{user.id}_id_card.png'),
        user=user
    )

@app.route('/profile/<int:id>')
def profile(id):
    user = UserSubmission.query.get_or_404(id)

    # Check if the QR code has expired
    if user.expiry_date and user.expiry_date < datetime.utcnow().date():
        return "This QR code has expired.", 403

    return render_template('profile.html', user=user)

@app.route('/admin')
def admin():
    submissions = UserSubmission.query.all()
    return render_template('admin.html', submissions=submissions)

@app.route('/admin/delete/<int:id>', methods=['POST'])
def delete_submission(id):
    submission = UserSubmission.query.get_or_404(id)
    db.session.delete(submission)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
def edit_submission(id):
    submission = UserSubmission.query.get_or_404(id)
    if request.method == 'POST':
        submission.name = request.form['name']
        submission.email = request.form['email']
        submission.phone = request.form['phone']
        submission.dob = datetime.strptime(request.form['dob'], '%Y-%m-%d').date()
        submission.gender = request.form['gender']
        submission.country = request.form['country']
        submission.comments = request.form['comments']
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit.html', submission=submission)

if __name__ == '__main__':
    app.run(debug=False)
