from flask import Flask, render_template, redirect

# Use Flask's standard project layout:
# - templates in `templates/`
# - static assets in `static/`
app = Flask(__name__, template_folder="templates", static_folder="static")


# Home redirects to the login page for this small frontend prototype.
@app.route("/")
def home():
    return redirect("/login")


# Render the login page. Backend auth is intentionally omitted for
# the current frontend-onlye form submits to `/login`
# so it can be wired to a backend later.
@app.route("/login", methods=["GET", "POST"])
def login():
    return render_template("loginpage.html")


# Render the registration page. The form requires a name field for
# first-time signups; server-side processing will come in a later task.
@app.route("/register", methods=["GET", "POST"])
def register():
    return render_template("registrationpage.html")


# Minimal placeholder route for admin access.
@app.route("/admin-login")
def admin_login():
    return "<h1>Admin Login Page Coming Soon</h1>"


if __name__ == "__main__":
    # Development server: easy to run during development for demos.
    app.run(debug=True)