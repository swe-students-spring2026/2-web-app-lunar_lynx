#!/usr/bin/env python3

"""
All routes and logic for the Flask web app.
See README.md for setup instructions.
"""

import os
import datetime
from flask import Flask, render_template, redirect, request, url_for, jsonify
import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

class User(UserMixin):
    """
    Simple wrapper around a MongoDB user document so flask-login can work with it.
    """

    def __init__(self, doc):
        self.doc = doc

    def get_id(self):
        return str(self.doc["_id"])

    @property
    def is_active(self):
        return self.doc.get("status", "active") == "active"

    @property
    def is_admin(self):
        return self.doc.get("role") == "admin"

def create_app():
    """
    Create and configure the Flask application.
    returns: app: the Flask application object
    """

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.getenv("SESSION_SECRET_KEY") # Needed for flask-login

    # MongoDB setup and test
    connection = pymongo.MongoClient(os.getenv("MONGO_URI"))
    db = connection[os.getenv("MONGO_DBNAME")]

    try:
        connection.admin.command("ping")
        print(" *", "Successfully connected to MongoDB")
    except Exception as e:
        print(" *", "Error connecting to MongoDB:", e)

    # Flask-login setup
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"  # Redirect to login page if not authenticated

    @login_manager.user_loader
    def load_user(user_id):
        """
        "This callback is used to reload the user object from
        the user ID stored in the session." - flask-login documentation
        Args:
            user_id (str): The ID of the user to load.
        Returns:
            User: A User object if found, otherwise None.
        """
        try:
            oid = ObjectId(user_id)
        except Exception:
            return None

        doc = db.users.find_one({"_id": oid})
        if doc:
            return User(doc)
        return None

    ### Page Routes (HTML) ###

    @app.route("/")
    def home():
        """
        Route for the home page.
        """
        if current_user.is_authenticated:
            # TODO: change maybe
            return render_template("profile.html")
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """
        Route for the login page.
        """
        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")

            doc = db.users.find_one({"email": email})

            if not doc or not check_password_hash(doc["password_hash"], password):
                return render_template("loginpage.html", error="Invalid email or password")

            user = User(doc)
            login_user(user)

            db.users.update_one(
                {"_id": doc["_id"]},
                {"$set": {"last_login_at": datetime.datetime.utcnow()}}
            )

            next_url = request.args.get("next") or url_for("home")
            return redirect(next_url)

        return render_template("loginpage.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        """
        Route for the registration page.
        """
        if request.method == "POST":
            full_name = request.form.get("full_name")
            netid = request.form.get("netid")
            email = request.form.get("email")
            password = request.form.get("password")

            if not netid or not email or not password:
                return render_template(
                    "registrationpage.html",
                    error="NetID, email, and password are required.",
                )

            existing = db.users.find_one({"email": email})
            if existing:
                return render_template(
                    "registrationpage.html",
                    error="User with that email already exists.",
                )

            doc = {
                "full_name": full_name,
                "netid": netid,
                "email": email,
                "password_hash": generate_password_hash(password),
                "role": "user",
                "status": "active",
                "created_at": datetime.datetime.utcnow(),
                "last_login_at": None,
            }

            result = db.users.insert_one(doc)
            doc["_id"] = result.inserted_id

            # Auto-login after registration
            user = User(doc)
            login_user(user)

            return redirect(url_for("home"))

        return render_template("registrationpage.html")

    @app.route("/logout")
    @login_required
    def logout():
        """
        Route for logging out the user.
        Returns:
            redirect (Response): A redirect response to the login page.
        """
        logout_user()
        return redirect(url_for("login"))

    @app.errorhandler(Exception)
    def handle_error(e):
        """
        Output any errors - good for debugging.
        Args:
            e (Exception): The exception object.
        Returns:
            rendered template (str): The rendered HTML template.
        """
        return render_template("error.html", error=e)

    return app

app = create_app()

# Run Flask application directly
if __name__ == "__main__":
    FLASK_PORT = os.getenv("FLASK_PORT", "5000")
    FLASK_ENV = os.getenv("FLASK_ENV")
    print(f"FLASK_ENV: {FLASK_ENV}, FLASK_PORT: {FLASK_PORT}")

    app.run(port=FLASK_PORT)
