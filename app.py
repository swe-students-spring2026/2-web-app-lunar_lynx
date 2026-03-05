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
    @login_required
    def home():
        """
        Home page: show most recent posts.
        """
        posts = list(
            db.posts.find({"status": "open"}).sort("created_at", -1).limit(50)
        )

        for post in posts:
            user_doc = db.users.find_one({"_id": post["created_by"]})
            if user_doc:
                post["author_name"] = user_doc.get("full_name", "Unknown")
                post["author_id"] = str(user_doc["_id"])
            else:
                post["author_name"] = "Unknown"
                post["author_id"] = None

        return render_template("home.html", posts=posts)
    
    @app.route("/profile/edit", methods=["GET", "POST"])
    @login_required
    def edit_profile():
        """
        Edit current user's profile.
        """
        user_id = current_user.get_id()
        user_doc = db.users.find_one({"_id": ObjectId(user_id)})

        if not user_doc:
            return "User not found.", 404

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            netid = request.form.get("netid", "").strip()
            email = request.form.get("email", "").strip()

            if not full_name or not netid or not email:
                return render_template("edit_profile.html", user=user_doc, error="All fields are required.")

            db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "full_name": full_name,
                    "netid": netid,
                    "email": email
                }}
            )

            return redirect(url_for("profile"))

        return render_template("edit_profile.html", user=user_doc)

    @app.route("/search", methods=["GET"])
    @login_required
    def search():
        """
        Search posts by keyword in title/description.
        Reuses home.html to display results.
        """
        query = (request.args.get("query") or "").strip()

        if not query:
            # If empty search, just go back home
            return redirect(url_for("home"))

        # Simple regex search (case-insensitive) over title/description
        filter_q = {
            "status": "open",
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
            ],
        }

        posts = list(db.posts.find(filter_q).sort("created_at", -1).limit(50))
        return render_template("home.html", posts=posts)
    
    @app.route("/posts/new", methods=["GET"])
    @login_required
    def new_post():
        """
        Show the create-post form.
        """
        return render_template("new_post.html")
    
    @app.route("/posts", methods=["POST"])
    @login_required
    def create_post():
        """
        Handle create-post form submission.
        Inserts a post into MongoDB, then redirects home.
        """
        post_type = (request.form.get("type") or "").strip().lower()
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        location_text = (request.form.get("location_text") or "").strip()
        date_str = (request.form.get("date_lost_or_found") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        email = (request.form.get("email") or "").strip()
        other = (request.form.get("other_contact") or "").strip()

        # Basic validation
        if post_type not in {"lost", "found"} or not title or not description:
            return "Invalid post data", 400

        # Parse optional date (YYYY-MM-DD)
        date_lost_or_found = None
        if date_str:
            try:
                date_lost_or_found = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(
                    tzinfo=datetime.timezone.utc
                )
            except ValueError:
                return "Invalid date format", 400

        now = datetime.datetime.now(datetime.timezone.utc)

        doc = {
            "title": title,
            "description": description,
            "type": post_type,
            "status": "open",
            "location_text": location_text if location_text else None,
            "date_lost_or_found": date_lost_or_found,

            "contact": {
                "phone": phone if phone else None,
                "email": email if email else None,
                "other": other if other else None,
            },

            "created_by": ObjectId(current_user.get_id()),
            "created_at": now,
            "updated_at": now,
        }

        db.posts.insert_one(doc)
        return redirect(url_for("home"))

    @app.route("/posts/<post_id>", methods=["GET"])
    @login_required
    def post_detail(post_id):
        """
        View a single post by id.
        """
        try:
            oid = ObjectId(post_id)
        except Exception:
            return "Invalid post id", 400

        post = db.posts.find_one({"_id": oid})
        if not post:
            return "Post not found", 404
        
        user_doc = db.users.find_one({"_id": post["created_by"]})
        if user_doc:
            post["author_name"] = user_doc.get("full_name", "Unknown")
            post["author_id"] = str(user_doc["_id"])
        else:
            post["author_name"] = "Unknown"
            post["author_id"] = None

        return render_template("post_detail.html", post=post)
    
    @app.route("/profile/<user_id>")
    @login_required
    def profile_by_id(user_id):
        try:
            oid = ObjectId(user_id)
        except Exception:
            return "Invalid user id", 400

        user_doc = db.users.find_one({"_id": oid})
        if not user_doc:
            return "User not found", 404

        user_posts = list(db.posts.find({"created_by": oid}).sort("created_at", -1))
        return render_template("profile.html", user=user_doc, posts=user_posts)
    
    @app.route("/posts/<post_id>/status", methods=["POST"])
    @login_required
    def update_post_status(post_id):
        """
        Update a post's status (creator or admin only).
        """
        try:
            oid = ObjectId(post_id)
        except Exception:
            return "Invalid post id", 400

        post = db.posts.find_one({"_id": oid})
        if not post:
            return "Post not found", 404

        # Permission: only creator or admin
        try:
            current_oid = ObjectId(current_user.get_id())
        except Exception:
            return "Invalid user id", 400

        is_owner = post.get("created_by") == current_oid
        if not (is_owner or current_user.is_admin):
            return "Forbidden", 403

        new_status = (request.form.get("status") or "").strip().lower()
        allowed = {"open", "claimed", "resolved"}
        if new_status not in allowed:
            return "Invalid status", 400

        now = datetime.datetime.now(datetime.timezone.utc)

        db.posts.update_one(
            {"_id": oid},
            {"$set": {"status": new_status, "updated_at": now}},
        )

        return redirect(url_for("post_detail", post_id=post_id))
    
    @app.route("/posts/<post_id>/delete", methods=["POST"])
    @login_required
    def delete_post(post_id):
        """
        Delete a post (creator or admin only).
        """
        try:
            oid = ObjectId(post_id)
        except Exception:
            return "Invalid post id", 400

        post = db.posts.find_one({"_id": oid})
        if not post:
            return "Post not found", 404

        # Permission: only creator or admin
        try:
            current_oid = ObjectId(current_user.get_id())
        except Exception:
            return "Invalid user id", 400

        is_owner = post.get("created_by") == current_oid
        if not (is_owner or current_user.is_admin):
            return "Forbidden", 403

        db.posts.delete_one({"_id": oid})
        return redirect(url_for("home"))

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
                return render_template("login.html", error="Invalid email or password")

            user = User(doc)
            login_user(user)

            db.users.update_one(
                {"_id": doc["_id"]},
                {"$set": {"last_login_at": datetime.datetime.now(datetime.timezone.utc)}}
            )

            next_url = request.args.get("next") or url_for("home")
            return redirect(next_url)

        return render_template("login.html")

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
                    "register.html",
                    error="NetID, email, and password are required.",
                )

            existing = db.users.find_one({"email": email})
            if existing:
                return render_template(
                    "register.html", error="User with that email already exists.",
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

        return render_template("register.html")

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
        return "error"
    
    @app.route("/profile")
    @login_required
    def profile():
        """
        User profile page.
        """
        user_id = current_user.get_id()
        user_doc = db.users.find_one({"_id": ObjectId(user_id)})

        if not user_doc:
            return "User not found.", 404

        user_posts = list(db.posts.find({"created_by": ObjectId(user_id)}).sort("created_at", -1))

        return render_template("profile.html", user=user_doc, posts=user_posts)

    return app

app = create_app()

# Run Flask application directly
if __name__ == "__main__":
    FLASK_PORT = os.getenv("FLASK_PORT", "5000")
    FLASK_ENV = os.getenv("FLASK_ENV")
    print(f"FLASK_ENV: {FLASK_ENV}, FLASK_PORT: {FLASK_PORT}")

    app.run(port=FLASK_PORT)
