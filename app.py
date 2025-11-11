import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(APP_ROOT, 'uploads')
STATIC_FILES = APP_ROOT  # serve html/css from project root

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder=None)
CORS(app)  # allow cross-origin if user opens HTML directly without the server


@app.route('/')
def serve_index():
    return send_from_directory(STATIC_FILES, 'index.html')


@app.get('/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/analyze.html')
def serve_analyze_page():
    return send_from_directory(STATIC_FILES, 'analyze.html')


@app.route('/stats.html')
def serve_stats_page():
    return send_from_directory(STATIC_FILES, 'stats.html')


@app.route('/index.css')
def serve_css():
    return send_from_directory(STATIC_FILES, 'index.css')


@app.post('/analyze')
def analyze_video():
    if 'file' not in request.files:
        return jsonify({'error': '沒有收到檔案欄位 file'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': '未選擇檔案'}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_DIR, filename)
    try:
        file.save(save_path)
    except Exception as e:
        return jsonify({'error': f'無法儲存檔案: {e}'}), 500

    try:
        # Lazy import to avoid heavy imports failing before server starts
        from user_movid_predict import predict_video  # noqa: WPS433
        result = predict_video(save_path)
        if not result:
            return jsonify({'error': '分析失敗或回傳結果為空'}), 500

        # Normalize keys for frontend consumption
        return jsonify({
            'predicted_class': result.get('predicted_class'),
            'confidence': result.get('confidence'),
            'probabilities': result.get('probabilities', {}),
            'filename': filename
        })
    except Exception as e:
        return jsonify({'error': f'分析時發生錯誤: {e}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

