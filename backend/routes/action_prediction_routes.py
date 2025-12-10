"""
動作標準預測路由
處理影片上傳和動作標準預測
"""
from flask import request, jsonify
from werkzeug.utils import secure_filename
import os
from . import action_prediction_bp
from config import get_config

config = get_config()


@action_prediction_bp.route('/action-prediction', methods=['POST'])
def predict_action():
    """預測上傳的桌球動作影片是否標準"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '沒有收到檔案欄位 file'
            }), 400

        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({
                'success': False,
                'error': '未選擇檔案'
            }), 400

        # 儲存影片
        filename = secure_filename(file.filename)
        save_path = os.path.join(config.paths.UPLOAD_DIR, filename)
        
        try:
            file.save(save_path)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'無法儲存檔案: {e}'
            }), 500

        # 延遲導入避免啟動時載入過重
        from services.action_prediction_service import ActionPredictionService
        prediction_service = ActionPredictionService()
        
        print(f"🎬 開始預測動作標準: {filename}")
        result = prediction_service.predict(save_path)
        
        if not result:
            return jsonify({
                'success': False,
                'error': '預測失敗或回傳結果為空'
            }), 500

        return jsonify({
            'success': True,
            'prediction': result.get('prediction'),
            'confidence': result.get('confidence'),
            'probabilities': result.get('probabilities', {}),
            'filename': filename
        }), 200

    except Exception as e:
        print(f"❌ 預測失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

