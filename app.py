from flask import Flask, render_template, redirect, url_for, request, send_file, flash, session
import boto3
from flask_sqlalchemy import SQLAlchemy
import uuid, os, io
import datetime
from datetime import  timedelta
import xml.etree.ElementTree as ET
import random
from flask_migrate import Migrate
import aws_encryption_sdk
from aws_encryption_sdk import CommitmentPolicy
import zipfile
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask import jsonify
from hashlib import sha256
from email_validator import validate_email, EmailNotValidError
from validate_password import validate_password
import configparser

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
SIZE_LIMIT = 100 * 1024 * 1024 # 100 MB in bytes
CODE = 0

config = configparser.ConfigParser()
config.read('config.ini')

KEY_ARN = config.get('AWS', 'KEY_ARN')
S3_BUCKET = config.get('AWS', 'S3_BUCKET')
S3_REGION = config.get('AWS', 'S3_REGION')

EXPIRATION_TIME_DICT = {
    "10-minutes" : 10,
    "60-minutes" : 60,
    "1-day" :  1,
    "30-days" : 30,
    "90-days" : 90
}

client = aws_encryption_sdk.EncryptionSDKClient(
    commitment_policy=CommitmentPolicy.REQUIRE_ENCRYPT_REQUIRE_DECRYPT
)

master_key_provider = aws_encryption_sdk.StrictAwsKmsMasterKeyProvider(key_ids=[KEY_ARN])
db = SQLAlchemy()

s3 = boto3.resource("s3")
bucket = s3.Bucket(S3_BUCKET)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(100))
    filename = db.Column(db.String(100))
    bucket = db.Column(db.String(100))
    region = db.Column(db.String(100))
    file_code = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow())
    user = db.Column(db.String(100))
    access_level = db.Column(db.String(100), nullable=False, default='anyone')
    def __repr__(self):
        return f"File('{self.filename}, '{self.created_at})'"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique = True, nullable=False)
    password = db.Column(db.String(120), nullable = False)
    email = db.Column(db.String(120), nullable = False)
    def __repr__(self):
        return f"User({self.username} , {self.email})"


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Delete entry from database based on ID
def delete_file_by_id(id):
    entry_to_delete = File.query.get(id)
    db.session.delete(entry_to_delete)
    db.session.commit()

def delete_file_by_name(filename):
    entry_to_delete = File.query.filter_by(filename=filename).first()
    if entry_to_delete:
        db.session.delete(entry_to_delete)
        db.session.commit()
        return True
    return False

# deletes an entry from the database based on the original name
def delete_file_by_original_filename(original_filename):
    entry_to_delete = File.query.filter_by(original_filename=original_filename).first()
    if entry_to_delete:
        db.session.delete(entry_to_delete)
        db.session.commit()
        return entry_to_delete.filename
    return False

def delete_file_by_file_code(file_code):
    entry_to_delete = File.query.filter_by(file_code = file_code).first()
    if entry_to_delete:
        db.session.delete(entry_to_delete)
        db.session.commit()
        return entry_to_delete.filename
    return False

# wipes both the s3 bucket and the database
def wipe_data():
    for obj in bucket.objects.all():
        if obj.key:
            if check_db(obj.key):
                delete_file_by_name(obj.key)
            s3.Object(S3_BUCKET, obj.key).delete()

# function to check if a file is in the database 
def check_db(object_name):
    files = File.query.all()
    for file in files:
        if object_name == file.filename:
            return True
    return False

def check_original_name_in_database(filename):
    files = File.query.all()
    for file in files:
        if filename == file.filename:
            return file.original_filename

# deletes a file from s3 based on the filename
def delete_s3(filename):
    s3.Object(S3_BUCKET, filename).delete()

# function to upload a file to both s3 and the database
def upload_file(uploaded_file, encrypted_buffer, new_filename, user, access_level, archive = False):
    s3_client = boto3.client('s3', region_name=S3_REGION)
    s3_client.upload_fileobj(encrypted_buffer, S3_BUCKET, new_filename)
    code = random.randint(1e5, 1e6 - 1)
    if not archive:
        original_filename = uploaded_file.filename
    else:
        name, ext = os.path.splitext(uploaded_file[0].filename)
        original_filename = name + '.rar'
    file = File(original_filename=original_filename, filename=new_filename,
        bucket=S3_BUCKET, region=S3_REGION, file_code = int(code), user=user, access_level = access_level)
    db.session.add(file)
    db.session.commit()
    return code

# function to delete files after a period of time
def delete_expired_files(time, user):
    user == None if time == 10 else None
    if int(time) == 10 or int(time) == 60:
        expired_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
    else:
        expired_time = datetime.datetime.utcnow() - datetime.timedelta(days=time)
    has_expired_files = True
    while has_expired_files:
        expired_files = File.query.filter(File.created_at <= expired_time, File.user == user).all()
        for file in expired_files:
            db.session.delete(file)
            delete_s3(file.filename)
        db.session.commit()
        has_expired_files = File.query.filter(File.created_at <= expired_time, File.user == user).count() > 0
    # Return from the function
    return

def print_database(DB):
    entries = DB.query.all()
    for entry in entries:
        print(entry.__dict__)



def check_key_in_db(key):
    files = File.query.all()
    for file in files:
        if int(key) == int(file.file_code):
            return file.filename , file.user, file.access_level
    return False , False, False

def encrypt_files(uploaded_file):
    encrypted_buffer = io.BytesIO()
    with client.stream(mode = 'encrypt', source = uploaded_file, key_provider = master_key_provider) as encryptor:
        for chunk in encryptor:
            encrypted_buffer.write(chunk)
    encrypted_buffer.seek(0)
    return encrypted_buffer

def decrypt_files(encrypted_file):
    encrypted_buffer = io.BytesIO(encrypted_file['Body'].read())
    decrypted_buffer = io.BytesIO()
    with client.stream(mode='decrypt', source=encrypted_buffer, key_provider = master_key_provider) as decryptor:
        for chunk in decryptor:
            decrypted_buffer.write(chunk)
    decrypted_buffer.seek(0)
    return decrypted_buffer

def create_app():
    app = Flask(__name__)
    app.permanent_session_lifetime = timedelta(days=1)
    app.secret_key = uuid.uuid4().hex
    CORS(app)
    migrate = Migrate(app, db)
    app.config['DEBUG'] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite3"

    db.init_app(app)

    @app.route("/", methods=["GET", "POST"])
    def index():
        print_database(File)
        if 'user' in session:
            user = session['user']
        else:
            user = None
        global CODE
        if request.method == "POST":
            action = request.form.get('action')
            expiration_time = request.form.get('expirationTime')
            access_level = request.form.get('accessLevel')
            print(access_level)
            if action == 'upload':
                time = EXPIRATION_TIME_DICT[expiration_time]
                delete_expired_files(time, user)
                uploaded_files = request.files.getlist('file')
                for file in uploaded_files:
                    if not allowed_file(file.filename):
                        redirect(url_for('mylinks'))
                    if file.content_length > SIZE_LIMIT:
                        return 'ERROR'
                if len(uploaded_files) > 1:
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zipf:
                        for file in uploaded_files:
                            zipf.writestr(file.filename, file.read())
                    zip_buffer.seek(0)
                    new_filename = uuid.uuid4().hex + '.' + 'zip'
                    encrypted = encrypt_files(zip_buffer)
                    archive = True
                else:
                    archive = False
                    uploaded_files = uploaded_files[0]
                    new_filename = uuid.uuid4().hex + '.' + uploaded_files.filename.rsplit('.', 1)[1].lower()
                    encrypted = encrypt_files(uploaded_files)
                CODE = upload_file(uploaded_files, encrypted, new_filename, user, access_level, archive)
                return redirect(url_for("index"))
            elif action == 'download':
                key = request.form['input_key']
                output, file_user, file_access_level = check_key_in_db(key)
                if output:
                    if file_user == user and file_access_level == 'only-me':
                        return redirect(url_for('download_file', filename = output))
                    elif file_access_level == 'anyone':
                        return redirect(url_for('download_file', filename = output))
                    else:
                        error_message = 'YOU HAVE NO ACCESS'
                        return render_template('index.html', error_message=error_message)
                error_message = 'ERROR: Invalid Code'
                return render_template('index.html', error_message=error_message)
        files = File.query.all()
        return render_template("index.html", files=files)
    
    @app.route("/my_links", methods=["GET", "POST"])
    def mylinks():
        if 'user' not in session:
            user = None
            return redirect(url_for("login"))
        else:
            user = session['user']
        files = File.query.filter_by(user = user).all()
        return render_template("mylinks.html", files=files)

    @app.route("/delete-file", methods=["POST"])
    def delete_file():
        file_code = request.form.get("file_code")
        delete_s3(delete_file_by_file_code(file_code))
        return "FILE DELETED SUCCESSFULLY"
    
    @app.route('/get_code')
    def get_code():
        return jsonify(code=CODE)
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if ('user' in session):
            return redirect(url_for('index'))
        if request.method == 'GET':
            return render_template("login.html")
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'login':
                username = request.form['username']
                password = request.form['password']
                if not username or not password:
                    flash('invalid credentials')
                    return redirect(url_for('login'))
                encrypted_password = sha256(password.encode()).hexdigest()
                user = User.query.filter_by(username=username, password=encrypted_password).first()
                if user:
                    session['user'] = username
                    session.permanent = True
                    return redirect(url_for('index'))
                flash('invalid credentials')
                return redirect(url_for('login'))
            elif action == 'register':
                try:
                    username = request.form['username']
                    password = request.form['password']
                    email = request.form['email']
                    user = User.query.filter_by(username=username).first()
                    if user:
                        flash('username is taken')
                        return redirect(url_for('login'))
                    if(not validate_password(password)):
                        flash('invalid password')
                        return redirect(url_for('login'))
                    encrypted_password = sha256(password.encode()).hexdigest()
                except:
                    flash('invalid input')
                    return redirect(url_for('login'))
                try:
                    email_checker = User.query.filter_by(email=email).first()
                    if email_checker:
                        flash('email is taken')
                        return redirect(url_for('login'))
                    validation = validate_email(email)
                    email = validation.email
                except EmailNotValidError as e:
                    flash(str(e))
                    return redirect(url_for('login'))
                user = User.query.filter_by(username=username).first()
                if user:
                    flash('invalid credentials')
                    return redirect(url_for('login'))
                user = User(username=username, password=encrypted_password, email=email)
                db.session.add(user)
                db.session.commit()
                if user:
                    session['user'] = username
                    session.permanent = True
                    return redirect(url_for('index'))
                return redirect(url_for('login'))

    @app.route('/logout', methods=['GET'])
    def logout():
        if request.method == 'GET':
            session.pop('user', None)
            return redirect(url_for('index'))

    @app.route('/download/<filename>', methods=['GET'])
    def download_file(filename):
        original_name = check_original_name_in_database(filename)
        s3_client = boto3.client('s3', region_name = S3_REGION)
        try:
            encrypted_file = s3_client.get_object(Bucket=S3_BUCKET, Key=filename)
        except:
            return "ERROR"
        decrypted_buffer = decrypt_files(encrypted_file)
        return send_file(decrypted_buffer, download_name=original_name, mimetype='application/octet-stream', as_attachment=True)
    return app
