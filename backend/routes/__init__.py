"""
路由模組
包含所有 API 端點的路由藍圖
"""
from flask import Blueprint

# 建立藍圖
health_bp = Blueprint('health', __name__)
ranking_bp = Blueprint('ranking', __name__, url_prefix='/api')
analysis_bp = Blueprint('analysis', __name__, url_prefix='/api')
training_bp = Blueprint('training', __name__, url_prefix='/api')
failure_bp = Blueprint('failure', __name__, url_prefix='/api')
youtube_bp = Blueprint('youtube', __name__, url_prefix='/api')
player_bp = Blueprint('player', __name__, url_prefix='/api/players')
auto_train_bp = Blueprint('auto_train', __name__, url_prefix='/api/auto-train')
predict_bp = Blueprint('predict', __name__, url_prefix='/api/predict')
action_prediction_bp = Blueprint('action_prediction', __name__, url_prefix='/api')

# 導入路由處理器
from . import health_routes
from . import ranking_routes
from . import analysis_routes
from . import training_routes
from . import failure_routes
from . import youtube_routes
from . import player_routes
from . import auto_train_routes
from . import predict_routes
from . import action_prediction_routes


def register_blueprints(app):
    """註冊所有藍圖到應用程式"""
    app.register_blueprint(health_bp)
    app.register_blueprint(ranking_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(training_bp)
    app.register_blueprint(failure_bp)
    app.register_blueprint(youtube_bp)
    app.register_blueprint(player_bp)
    app.register_blueprint(action_prediction_bp)
    # app.register_blueprint(auto_train_bp)  # 在 app.py 中單獨註冊
    # app.register_blueprint(predict_bp)     # 在 app.py 中單獨註冊
