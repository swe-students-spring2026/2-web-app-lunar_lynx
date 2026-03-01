from flask import Flask, request, jsonify
from db import db
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

app = Flask(__name__)

# Users API

# Register
@app.route("/register", methods=["POST"])
def register_user():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Empty email or password."}), 400

    if db["users"].find_one({"email": email}):
        return jsonify({"error": "Email already registered."}), 400

    hashed_pw = generate_password_hash(password)
    user_id = db["users"].insert_one({
        "email": email,
        "password": hashed_pw
    }).inserted_id

    return jsonify({"message": "Successfully registered!", "user_id": str(user_id)}), 201

# Login
@app.route("/login", methods=["POST"])
def login_user():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = db["users"].find_one({"email": email})
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    return jsonify({"message": "Logged in!", "user_id": str(user["_id"])})


# Get user information
@app.route("/users/<user_id>", methods=["GET"])
def get_user(user_id):
    user = db["users"].find_one({"_id": ObjectId(user_id)}, {"password": 0})
    if not user:
        return jsonify({"error": "User not exist."}), 404
    user["_id"] = str(user["_id"])
    return jsonify(user)


# Posts API

# Create posts
@app.route("/users/posts/create", methods=["POST"])
def create_post():
    data = request.json
    name = data.get("name")
    location = data.get("location")
    description = data.get("description")

    if not name or not location or not description:
        return jsonify({"error": "Please suggest your name/location/description."}), 400

    post_id = db["posts"].insert_one({
        "name": name,
        "location": location,
        "description": description
    }).inserted_id

    return jsonify({"message": "Post created.", "post_id": str(post_id)}), 201

# Get all posts
@app.route("/users/posts", methods=["GET"])
def get_all_posts():
    posts = list(db["posts"].find())
    for p in posts:
        p["_id"] = str(p["_id"])
    return jsonify(posts)

# Get a single post
@app.route("/users/posts/<post_id>", methods=["GET"])
def get_post(post_id):
    post = db["posts"].find_one({"_id": ObjectId(post_id)})
    if not post:
        return jsonify({"error": "Post not exist."}), 404
    post["_id"] = str(post["_id"])
    return jsonify(post)

# Edit post
@app.route("/users/posts/<post_id>", methods=["PUT"])
def edit_post(post_id):
    data = request.json
    db["posts"].update_one(
        {"_id": ObjectId(post_id)},
        {"$set": {"name": data.get("name"), "location": data.get("location"), "description": data.get("description")}}
    )
    return jsonify({"message": "Post updated."})

# Delete post
@app.route("/users/posts/<post_id>", methods=["DELETE"])
def delete_post(post_id):
    db["posts"].delete_one({"_id": ObjectId(post_id)})
    return jsonify({"message": "Post deleted."})


# Run Flask
if __name__ == "__main__":
    app.run(debug=True)