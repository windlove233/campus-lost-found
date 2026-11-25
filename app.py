from flask import Flask

from routes.search import search_bp

from routes.publish import publish_bp

app = Flask(__name__)
app.register_blueprint(search_bp)
app.register_blueprint(publish_bp)