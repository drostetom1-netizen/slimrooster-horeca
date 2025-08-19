from flask import Flask, request

app = Flask(__name__)

@app.route("/", methods=["GET"])
def hello():
    return "Hello from Flask on Vercel!"

# Voeg hier jouw routes toe

def handler(environ, start_response):
    return app(environ, start_response)