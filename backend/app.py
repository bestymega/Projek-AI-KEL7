from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Backend BST berjalan"

if __name__ == "__main__":
    app.run(debug=True)