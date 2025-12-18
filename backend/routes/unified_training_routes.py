"""
統一訓練 API 路由
支援簡單分類和技術分類訓練
"""
from flask import Blueprint, request, jsonify
import uuid
import threading
import os
from services.unified_training_service import (
    get_unified_training_service,
    TrainingConfig,
    TrainingMode,
    ModelArchitecture
)

unified_training_bp = Blueprint('unified_training', __name__, url_prefix='/api/unified-training')

# 訓練任務存儲
training_tasks = {}


@unified_training_bp.route('/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({
        "status": "ok",
        "service": "unified_training"
    })


@unified_training_bp.route('/stats', methods=['GET'])
def get_training_stats():
    """取得訓練數據統計"""
    try:
        service = get_unified_training_service()
        stats = service.get_training_data_stats()
        
        return jsonify({
            "success": True,
            "stats": stats
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@unified_training_bp.route('/train', methods=['POST'])
def start_training():
    """
    啟動訓練任務
    
    Request Body:
        - mode: "simple" 或 "technique"
        - architecture: "basic", "bidirectional", "deep", "advanced"
        - epochs: 訓練輪數 (預設 100)
        - batch_size: 批次大小 (預設 32)
        - learning_rate: 學習率 (預設 0.001)
        - use_augmentation: 是否使用數據增強 (預設 True)
        - augment_factor: 增強倍數 (預設 3)
        - use_class_weights: 是否使用類別權重 (預設 True)
    """
    try:
        data = request.get_json() or {}
        
        # 解析配置
        config = TrainingConfig(
            mode=data.get('mode', 'simple'),
            architecture=data.get('architecture', 'basic'),
            epochs=data.get('epochs', 100),
            batch_size=data.get('batch_size', 32),
            learning_rate=data.get('learning_rate', 0.001),
            use_augmentation=data.get('use_augmentation', True),
            augment_factor=data.get('augment_factor', 3),
            early_stop_patience=data.get('early_stop_patience', 15),
            use_class_weights=data.get('use_class_weights', True),
            min_samples_per_class=data.get('min_samples_per_class', 5),
            test_size=data.get('test_size', 0.2)
        )
        
        # 驗證模式
        if config.mode not in ['simple', 'technique']:
            return jsonify({
                "success": False,
                "error": "無效的訓練模式，請使用 'simple' 或 'technique'"
            }), 400
        
        # 驗證架構
        valid_architectures = ['basic', 'bidirectional', 'deep', 'advanced']
        if config.architecture not in valid_architectures:
            return jsonify({
                "success": False,
                "error": f"無效的模型架構，請使用: {valid_architectures}"
            }), 400
        
        # 檢查訓練數據
        service = get_unified_training_service()
        stats = service.get_training_data_stats()
        
        if config.mode == 'simple' and not stats['simple']['ready_for_training']:
            return jsonify({
                "success": False,
                "error": "訓練數據不足，每個類別至少需要 5 個樣本",
                "stats": stats['simple']
            }), 400
        
        if config.mode == 'technique' and not stats['technique']['ready_for_training']:
            return jsonify({
                "success": False,
                "error": "訓練數據不足，至少需要 3 個類別，每個類別至少 5 個樣本",
                "stats": stats['technique']
            }), 400
        
        # 生成任務 ID
        task_id = str(uuid.uuid4())
        
        # 初始化任務狀態
        training_tasks[task_id] = {
            'status': 'initializing',
            'message': '正在初始化訓練...',
            'config': config.to_dict(),
            'logs': [],
            'current_epoch': 0,
            'total_epochs': config.epochs,
            'accuracy': None,
            'val_accuracy': None,
            'loss': None,
            'val_loss': None,
            'result': None
        }
        
        # 在背景執行緒中執行訓練
        def run_training():
            try:
                training_tasks[task_id]['status'] = 'training'
                
                result = service.train(
                    config=config,
                    task_id=task_id,
                    task_storage=training_tasks
                )
                
                if result.success:
                    training_tasks[task_id]['status'] = 'completed'
                    training_tasks[task_id]['message'] = '訓練完成！'
                    training_tasks[task_id]['result'] = result.to_dict()
                else:
                    training_tasks[task_id]['status'] = 'failed'
                    training_tasks[task_id]['message'] = result.error_message or '訓練失敗'
                    
            except Exception as e:
                training_tasks[task_id]['status'] = 'failed'
                training_tasks[task_id]['message'] = str(e)
                training_tasks[task_id]['logs'].append(f"❌ 錯誤: {str(e)}")
        
        training_thread = threading.Thread(target=run_training)
        training_thread.daemon = True
        training_thread.start()
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "訓練已啟動",
            "config": config.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@unified_training_bp.route('/train/status/<task_id>', methods=['GET'])
def get_training_status(task_id: str):
    """取得訓練狀態"""
    if task_id not in training_tasks:
        return jsonify({
            "success": False,
            "error": "找不到該訓練任務"
        }), 404
    
    task = training_tasks[task_id]
    
    # 只返回最新的日誌
    recent_logs = task.get('logs', [])[-20:]
    
    response = {
        "success": True,
        "status": task['status'],
        "message": task.get('message', ''),
        "current_epoch": task.get('current_epoch', 0),
        "total_epochs": task.get('total_epochs', 0),
        "accuracy": task.get('accuracy'),
        "val_accuracy": task.get('val_accuracy'),
        "loss": task.get('loss'),
        "val_loss": task.get('val_loss'),
        "logs": recent_logs,
        "config": task.get('config')
    }
    
    if task['status'] == 'completed':
        response['result'] = task.get('result', {})
    
    return jsonify(response)


@unified_training_bp.route('/train/cancel/<task_id>', methods=['POST'])
def cancel_training(task_id: str):
    """取消訓練任務"""
    if task_id not in training_tasks:
        return jsonify({
            "success": False,
            "error": "找不到該訓練任務"
        }), 404
    
    training_tasks[task_id]['status'] = 'cancelled'
    training_tasks[task_id]['message'] = '訓練已取消'
    
    return jsonify({
        "success": True,
        "message": "訓練已取消"
    })


@unified_training_bp.route('/models', methods=['GET'])
def get_models():
    """取得模型列表"""
    try:
        service = get_unified_training_service()
        models = service.get_available_models()
        
        return jsonify({
            "success": True,
            "models": models,
            "count": len(models)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@unified_training_bp.route('/models/latest/<mode>', methods=['GET'])
def get_latest_model(mode: str):
    """取得最新模型"""
    try:
        if mode not in ['simple', 'technique']:
            return jsonify({
                "success": False,
                "error": "無效的模式"
            }), 400
        
        service = get_unified_training_service()
        model = service.get_latest_model(mode)
        
        if model is None:
            return jsonify({
                "success": False,
                "error": f"找不到 {mode} 模式的模型"
            }), 404
        
        return jsonify({
            "success": True,
            "model": model
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@unified_training_bp.route('/models/<filename>', methods=['DELETE'])
def delete_model(filename: str):
    """刪除模型"""
    try:
        service = get_unified_training_service()
        success = service.delete_model(filename)
        
        if not success:
            return jsonify({
                "success": False,
                "error": "模型不存在"
            }), 404
        
        return jsonify({
            "success": True,
            "message": "模型已刪除"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@unified_training_bp.route('/quick-train', methods=['POST'])
def quick_train():
    """
    一鍵快速訓練 - 使用預設配置
    
    Request Body:
        - mode: "simple" 或 "technique" (預設 "simple")
    """
    try:
        data = request.get_json() or {}
        mode = data.get('mode', 'simple')
        
        # 使用最佳預設配置
        default_config = {
            'mode': mode,
            'architecture': 'bidirectional',  # 雙向 LSTM 效果較好
            'epochs': 80,
            'batch_size': 32,
            'learning_rate': 0.001,
            'use_augmentation': True,
            'augment_factor': 3,
            'use_class_weights': True
        }
        
        # 轉發到正式訓練端點
        from flask import current_app
        with current_app.test_request_context(
            '/api/unified-training/train',
            method='POST',
            json=default_config
        ):
            return start_training()
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ==================== 預測相關端點 ====================

@unified_training_bp.route('/predict', methods=['POST'])
def predict_video():
    """
    預測影片動作
    
    Request Body:
        - video_path: 影片路徑 (必填)
        - model_type: 'lstm', 'r3d', 或 'auto' (預設 'auto')
        - mode: 'simple' 或 'technique' (預設 'simple', 僅用於 LSTM)
    """
    try:
        from services.enhanced_prediction_service import get_enhanced_prediction_service
        
        data = request.get_json() or {}
        video_path = data.get('video_path')
        model_type = data.get('model_type', 'auto')
        mode = data.get('mode', 'simple')
        
        if not video_path:
            return jsonify({
                "success": False,
                "error": "請提供影片路徑"
            }), 400
        
        # 處理相對路徑
        if not os.path.isabs(video_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            video_path = os.path.join(base_dir, video_path)
        
        service = get_enhanced_prediction_service()
        result = service.predict(video_path, model_type, mode)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@unified_training_bp.route('/predict/upload', methods=['POST'])
def predict_uploaded_video():
    """
    上傳並預測影片
    """
    try:
        from services.enhanced_prediction_service import get_enhanced_prediction_service
        from werkzeug.utils import secure_filename
        
        if 'video' not in request.files:
            return jsonify({
                "success": False,
                "error": "請上傳影片檔案"
            }), 400
        
        video_file = request.files['video']
        model_type = request.form.get('model_type', 'auto')
        mode = request.form.get('mode', 'simple')
        
        if video_file.filename == '':
            return jsonify({
                "success": False,
                "error": "請選擇影片檔案"
            }), 400
        
        # 儲存上傳的檔案
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        uploads_dir = os.path.join(base_dir, 'uploads', 'predict')
        os.makedirs(uploads_dir, exist_ok=True)
        
        filename = secure_filename(video_file.filename)
        video_path = os.path.join(uploads_dir, filename)
        video_file.save(video_path)
        
        # 預測
        service = get_enhanced_prediction_service()
        result = service.predict(video_path, model_type, mode)
        result['uploaded_path'] = video_path
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@unified_training_bp.route('/predict/available-models', methods=['GET'])
def get_available_prediction_models():
    """取得可用的預測模型"""
    try:
        from services.enhanced_prediction_service import get_enhanced_prediction_service
        
        service = get_enhanced_prediction_service()
        models = service.get_available_models()
        
        return jsonify({
            "success": True,
            "models": models
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

