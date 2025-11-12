import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler
import uuid
import threading
import time

CWD = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = CWD
UPLOAD_DIR = os.path.join(APP_ROOT, 'uploads')
DATA_DIR = os.path.join(APP_ROOT, 'data')
STATIC_FILES = APP_ROOT  # serve html/css from project root

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Let Flask serve static files from project root so pages work when served by the app
app = Flask(__name__, static_folder=STATIC_FILES)

# Configure CORS based on environment
allowed_origins = os.environ.get('ALLOWED_ORIGINS', '*')
if allowed_origins != '*':
    # 支援多個域名（逗號分隔）
    allowed_origins = [origin.strip() for origin in allowed_origins.split(',')]

CORS(app, origins=allowed_origins)  # allow cross-origin

# Initialize ranking crawler and scheduler
from crawler import TableTennisRankingCrawler
crawler = TableTennisRankingCrawler()

# Set up scheduler for auto-updating rankings every hour
scheduler = BackgroundScheduler()
scheduler.add_job(func=crawler.update_all_rankings, trigger="interval", hours=1)
scheduler.start()

# Global dictionary to store training tasks
training_tasks = {}


def run_training_task(task_id, config):
    """在背景執行訓練任務"""
    try:
        training_tasks[task_id]['status'] = 'training'
        training_tasks[task_id]['message'] = '正在準備資料...'
        training_tasks[task_id]['logs'] = []
        
        # 動態導入訓練腳本
        import train_web
        
        # 執行訓練（這會更新 training_tasks 中的進度）
        result = train_web.train_model(config, task_id, training_tasks)
        
        training_tasks[task_id]['status'] = 'completed'
        training_tasks[task_id]['result'] = result
        training_tasks[task_id]['message'] = '訓練完成！'
        
    except Exception as e:
        training_tasks[task_id]['status'] = 'failed'
        training_tasks[task_id]['message'] = str(e)
        training_tasks[task_id]['logs'].append(f"❌ 錯誤: {str(e)}")


@app.route('/')
def serve_index():
    return app.send_static_file('index.html')


@app.get('/health')
def health():
    return jsonify({'status': 'ok'})


# Alias for API consumers
@app.get('/api/health')
def api_health():
    return jsonify({'status': 'ok', 'message': 'Server is running'})


@app.route('/analyze.html')
def serve_analyze_page():
    return app.send_static_file('analyze.html')


@app.route('/stats.html')
def serve_stats_page():
    # this project uses player_data.html as the stats/player page
    return app.send_static_file('player_data.html')


@app.route('/index.css')
def serve_css():
    return app.send_static_file('index.css')


# NOTE: generic static route relocated to after API routes to avoid catching API calls


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


# ============ Ranking API Routes (from cloud_tennis) ============

@app.route('/api/rankings/<category>', methods=['GET'])
def get_ranking(category):
    """
    取得特定類別的排名資料
    category: SEN_SINGLES, SEN_DOUBLES
    """
    valid_categories = ['SEN_SINGLES', 'SEN_DOUBLES']
    
    if category not in valid_categories:
        return jsonify({
            'error': '無效的類別',
            'valid_categories': valid_categories
        }), 400
    
    # 先嘗試讀取已儲存的資料
    data = crawler.load_data(category)
    
    # 如果沒有資料,立即抓取
    if not data:
        print(f"首次抓取 {category} 資料...")
        raw_data = crawler.fetch_ranking(category)
        if raw_data:
            data = crawler.load_data(category)
    
    if data:
        # 篩選出 SubEventCode 為 MS 或 MD 的選手
        if 'data' in data and 'Result' in data['data']:
            original_result = data['data']['Result']
            
            # 根據類別篩選
            if category == 'SEN_SINGLES':
                # 只保留 MS (男子單打)
                filtered_result = [
                    player for player in original_result 
                    if player.get('SubEventCode') == 'MS'
                ]
            elif category == 'SEN_DOUBLES':
                # 只保留 MD (男子雙打)
                filtered_result = [
                    player for player in original_result 
                    if player.get('SubEventCode') == 'MD'
                ]
            else:
                filtered_result = original_result
            
            # 按照 CurrentRank 排序
            filtered_result.sort(key=lambda x: int(x.get('CurrentRank', 999999)))
            
            # 更新資料
            data['data']['Result'] = filtered_result
            data['data']['TotalRecords'] = len(filtered_result)
        
        return jsonify(data), 200
    else:
        return jsonify({'error': '無法取得資料'}), 500


@app.route('/api/rankings', methods=['GET'])
def get_all_rankings():
    """取得所有排名資料"""
    categories = ['SEN_SINGLES', 'SEN_DOUBLES']
    all_data = {}
    
    for category in categories:
        data = crawler.load_data(category)
        if data:
            all_data[category] = data
    
    return jsonify(all_data), 200


@app.route('/api/update', methods=['POST'])
def manual_update():
    """手動觸發資料更新"""
    results = crawler.update_all_rankings()
    return jsonify({
        'message': '更新完成',
        'results': results
    }), 200


@app.post('/api/train')
def start_training():
    """啟動模型訓練"""
    try:
        config = request.get_json()
        
        # 驗證配置
        required_fields = ['model_type', 'epochs', 'batch_size', 'learning_rate']
        for field in required_fields:
            if field not in config:
                return jsonify({'error': f'缺少必要參數: {field}'}), 400
        
        # 生成任務 ID
        task_id = str(uuid.uuid4())
        
        # 初始化任務狀態
        training_tasks[task_id] = {
            'status': 'initializing',
            'message': '正在初始化訓練...',
            'config': config,
            'logs': [],
            'current_epoch': 0,
            'total_epochs': config['epochs']
        }
        
        # 在背景執行緒中啟動訓練
        training_thread = threading.Thread(
            target=run_training_task,
            args=(task_id, config)
        )
        training_thread.daemon = True
        training_thread.start()
        
        return jsonify({
            'task_id': task_id,
            'message': '訓練已啟動'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.get('/api/train/status/<task_id>')
def get_training_status(task_id):
    """取得訓練狀態"""
    if task_id not in training_tasks:
        return jsonify({'error': '找不到該訓練任務'}), 404
    
    task = training_tasks[task_id]
    
    # 只返回最新的日誌（避免傳輸過大）
    recent_logs = task.get('logs', [])[-10:] if 'logs' in task else []
    
    response = {
        'status': task['status'],
        'message': task.get('message', ''),
        'current_epoch': task.get('current_epoch', 0),
        'total_epochs': task.get('total_epochs', 0),
        'accuracy': task.get('accuracy'),
        'val_accuracy': task.get('val_accuracy'),
        'loss': task.get('loss'),
        'val_loss': task.get('val_loss'),
        'logs': recent_logs
    }
    
    if task['status'] == 'completed':
        response['result'] = task.get('result', {})
    
    return jsonify(response), 200


# ============ Failure Analysis API Routes ============

@app.route('/api/analyze-failure', methods=['POST'])
def analyze_failure():
    """分析失分影片並提供 AI 建議"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '沒有收到檔案欄位 file'}), 400

        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': '未選擇檔案'}), 400

        # 儲存影片
        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_DIR, f'failure_{uuid.uuid4()}_{filename}')
        file.save(save_path)

        # 是否使用 Gemini AI
        use_gemini = request.form.get('use_gemini', 'true').lower() == 'true'
        
        # 初始化分析器
        from failure_analyzer import FailureAnalyzer
        analyzer = FailureAnalyzer()
        
        # 執行分析
        print(f"🎬 開始分析失誤影片: {filename}")
        result = analyzer.analyze_failure(save_path, use_gemini=use_gemini)
        
        # 返回結果
        return jsonify({
            'success': True,
            'filename': filename,
            'analysis': result,
            'video_path': save_path
        }), 200

    except Exception as e:
        print(f"❌ 分析失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analyze-failure/batch', methods=['POST'])
def analyze_failure_batch():
    """批次分析多個失誤影片"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': '沒有收到檔案欄位 files'}), 400

        files = request.files.getlist('files')
        if not files or len(files) == 0:
            return jsonify({'error': '未選擇檔案'}), 400

        use_gemini = request.form.get('use_gemini', 'true').lower() == 'true'
        
        from failure_analyzer import FailureAnalyzer
        analyzer = FailureAnalyzer()
        
        results = []
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                save_path = os.path.join(UPLOAD_DIR, f'failure_{uuid.uuid4()}_{filename}')
                file.save(save_path)
                
                try:
                    analysis = analyzer.analyze_failure(save_path, use_gemini=use_gemini)
                    results.append({
                        'filename': filename,
                        'success': True,
                        'analysis': analysis
                    })
                except Exception as e:
                    results.append({
                        'filename': filename,
                        'success': False,
                        'error': str(e)
                    })
        
        return jsonify({
            'total': len(files),
            'results': results
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze-failure/config', methods=['GET'])
def get_analysis_config():
    """取得分析配置資訊"""
    try:
        # 檢查 Gemini API 是否可用 - 實際初始化分析器來測試
        from failure_analyzer import FailureAnalyzer
        test_analyzer = FailureAnalyzer()
        gemini_available = test_analyzer.model is not None
        
        return jsonify({
            'gemini_available': gemini_available,
            'supported_formats': ['mp4', 'avi', 'mov', 'mkv'],
            'max_duration_seconds': 10,
            'recommended_duration_seconds': 4,
            'analysis_modes': {
                'basic': '基礎分析（僅使用 MediaPipe）',
                'gemini': 'AI 深度分析（使用 Gemini）'
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Generic static file route: allow fetching other files (images, css, js) from repo root
@app.route('/<path:filename>')
def serve_static_other(filename: str):
    # Security: only serve files that exist under project root
    full_path = os.path.join(STATIC_FILES, filename)
    if os.path.exists(full_path) and os.path.commonpath([APP_ROOT, os.path.abspath(full_path)]) == APP_ROOT:
        return send_from_directory(STATIC_FILES, filename)
    return jsonify({'error': 'file not found'}), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Initialize ranking data on startup
    print("初始化排名資料...")
    try:
        crawler.update_all_rankings()
    except Exception as e:
        print(f"初始化排名資料失敗: {e}")
    
    app.run(host='0.0.0.0', port=port, debug=True)

