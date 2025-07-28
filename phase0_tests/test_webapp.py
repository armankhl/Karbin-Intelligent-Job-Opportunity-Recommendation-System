from flask import Flask

# Create a Flask web application instance
app = Flask(__name__)

@app.route('/')
def home():
    """
    This function runs when someone visits the root URL ('/').
    """
    return "<h1>Hello, Job Seeker!</h1><p>This is the starting point for our recommendation system web app.</p>"

@app.route('/about')
def about():
    """ A simple about page. """
    return "<h2>About Page</h2><p>Project: Intelligent Job Recommendation System</p>"

if __name__ == "__main__":
    # Run the app in debug mode, which provides helpful error messages.
    # The app will be available at http://127.0.0.1:5000
    print("--- Starting Flask Web App ---")
    print("Visit http://127.0.0.1:5000 in your browser.")
    app.run(debug=True)