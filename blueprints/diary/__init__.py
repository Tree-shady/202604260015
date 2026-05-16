from flask import Blueprint

diary_bp = Blueprint('diary', __name__, url_prefix='/')

from . import routes
