from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
import pickle
import string
import nltk
from nltk.stem import PorterStemmer
import os
app = Flask(__name__)
app.secret_key = '1c8073775dbc85a92ce20ebd44fd6a4fd832078f59ef16ec'  # Replace with a secure secret key

# Initialize NLTK and models
ps = PorterStemmer()
tfidf = pickle.load(open('vectorizer.pkl', 'rb'))
model = pickle.load(open('model.pkl', 'rb'))

nltk.download('punkt')

def transform_text(text):
    text = text.lower()
    text = nltk.word_tokenize(text)

    y = []
    for i in text:
        if i.isalnum():
            y.append(i)

    text = y[:]
    y.clear()

    for i in text:
        if i not in string.punctuation:
            y.append(i)

    text = y[:]
    y.clear()

    for i in text:
        y.append(ps.stem(i))

    return " ".join(y)

# Define your database connection
db = pymysql.connect(
    host="autorack.proxy.rlwy.net",  # Your Railway MySQL host
    user="root",                     # Your MySQL username
    password="BJxWrCOjaFlXAuTdthieITxmzlgGuoND",  # Your MySQL password
    database="railway",              # Your MySQL database name
    port=24341,
    cursorclass=pymysql.cursors.DictCursor
)

# Create the 'app_users' table if it doesn't exist
def create_app_users_table():
    try:
        with db.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    full_name VARCHAR(255) NOT NULL,
                    username VARCHAR(255) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    phone VARCHAR(20) NOT NULL,
                    password VARCHAR(255) NOT NULL
                );
            """)
            db.commit()
            print("app_users table created or already exists.")
    except Exception as e:
        print(f"Error creating app_users table: {e}")

create_app_users_table()  # Ensure the table exists

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/index')
def index():
    if 'user' in session:
        return render_template('index.html')
    else:
        return redirect(url_for('signin'))

@app.route('/predict', methods=['POST'])
def predict():
    input_sms = request.form.get('message')
    transformed_sms = transform_text(input_sms)
    vector_input = tfidf.transform([transformed_sms])
    result = model.predict(vector_input)[0]
    prediction = "Spam" if result == 1 else "Not Spam"
    return render_template('result.html', prediction=prediction)

@app.route('/signin')
def signin():
    if 'user' in session:
        return redirect(url_for('index'))
    return render_template('signin.html')

@app.route('/signup', methods=['GET'])
def signup():
    return render_template('signup.html')

@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Password and Confirm Password do not match.", "error")
            return redirect('/signup')

        try:
            with db.cursor() as cur:
                cur.execute("""
                    INSERT INTO app_users (full_name, username, email, phone, password) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (full_name, username, email, phone, password))
                db.commit()
            flash('Registration successful', 'success')
        except Exception as e:
            flash(f"Error registering user: {e}", "error")
        return redirect('/signin')

    return "Invalid request method"

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember_me = request.form.get('remember_me')

        try:
            with db.cursor() as cur:
                cur.execute("SELECT * FROM app_users WHERE email = %s AND password = %s", (email, password))
                user = cur.fetchone()

            if user:
                session['user'] = user
                if remember_me:
                    session.permanent = True
                return redirect(url_for('index'))
            else:
                flash("Login failed. Check your email and password.", "error")
        except Exception as e:
            flash(f"Error during login: {e}", "error")
    return redirect('/signin')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
