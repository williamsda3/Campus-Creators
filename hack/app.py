from flask import Flask, render_template, request, redirect, url_for, session,flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_session import Session
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"


UPLOAD_FOLDER = 'images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Ensure the upload folder exists
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)
Session(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price_per_hour = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255))  # Assuming images are hosted elsewhere and accessed via URL
    category_tags = db.Column(db.String(255))  # Could be a comma-separated list or a relationship to another table
    rating = db.Column(db.Float)  # Average rating, possibly updated via a separate ratings model or table
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Linking a course to a user
    creator = relationship('User', backref='courses')  # Establishing a bidirectional relationship with the User model


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    course = db.relationship('Course', backref='bookings')  # This line establishes the relationship
    booked_on = db.Column(db.DateTime, nullable=False, default=datetime.now())

    def __repr__(self):
        return f'<Booking {self.id}>'

    def __repr__(self):
        return f'<Course {self.title}>'

@app.route('/')
def index():
    return render_template('index.html')  # Your landing page

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']  # Remember, hashing the password is important in a real app
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            # Redirect to dashboard after successful login
            return redirect(url_for('dashboard'))
        else:
            flash("You must be logged in to delete a course.")

            # return 'Invalid username or password'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    courses = Course.query.all()
    return render_template('dashboard.html', courses=courses)

@app.route('/profile')
def profile():
    return render_template('profile.html')  # Your landing page

@app.route('/create_course', methods=['GET', 'POST'])
def create_course():
    if 'user_id' not in session:
        return redirect(url_for('create_course'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price_per_hour = request.form['price_per_hour']
        category_tags = request.form['category_tags']
        image = request.files['image']
        
        file = request.files.get('image')  # Assuming 'image' is the name attribute in your <input type="file">
        if file and allowed_file(file.filename):  # 'allowed_file' checks for allowed extensions
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Construct the relative path for the image to be stored in the database
# After saving the image, before storing the path in the database
            image_url = os.path.join('images', filename).replace('\\', '/')
        else:
            image_url = 'default_image.png'  # Provide a default image path

        # You would likely want to add error checking and validation here

        new_course = Course(
            title=title,
            description=description,
            price_per_hour=price_per_hour,
            category_tags=category_tags,
            image_url=image_url,
            user_id=session['user_id']
        )
        db.session.add(new_course)
        db.session.commit()

        return redirect(url_for('dashboard'))
    return render_template('create_course.html')
from sqlalchemy.orm import joinedload

@app.route('/my_profile')
def my_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_courses = Course.query.filter_by(user_id=user_id).all()
    user_bookings = Booking.query.options(joinedload(Booking.course)).filter_by(user_id=user_id).all()
    return render_template('my_profile.html', courses=user_courses, bookings=user_bookings)


@app.route('/delete_course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    course_to_delete = Course.query.get_or_404(course_id)
    
    # Check if the current user is the creator of the course
    if course_to_delete.user_id != session['user_id']:
        # If not, do not allow them to delete it
        return redirect(url_for('my_profile'))
    
    db.session.delete(course_to_delete)
    db.session.commit()
    
    # Redirect to the profile page with a message about the deletion
    return redirect(url_for('my_profile'))

@app.route('/course/<int:course_id>')
def course_details(course_id):
    # Query the database for the course with the given course_id
    course = Course.query.get_or_404(course_id)
    return render_template('course_details.html', course=course)

@app.route('/book_course/<int:course_id>', methods=['POST'])
def book_course(course_id):
    if 'user_id' not in session:
        flash('Please log in to book courses.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    # Assuming you have a Course and Booking model set up already
    booking = Booking(user_id=user_id, course_id=course_id)
    db.session.add(booking)
    db.session.commit()
    flash('Your booking was successful!', 'success')

    return redirect(url_for('my_profile'))

@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    if 'user_id' not in session:
        flash('Please log in to cancel bookings.', 'warning')
        return redirect(url_for('login'))

    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id']:
        flash('You can only cancel your own bookings.', 'danger')
        return redirect(url_for('my_profile'))

    db.session.delete(booking)
    db.session.commit()
    flash('Booking cancelled successfully.', 'success')
    return redirect(url_for('my_profile'))


if __name__ == '__main__':
    with app.app_context():
     db.create_all()

    app.run(debug=True)
