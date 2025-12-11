"""
YouTube 分析路由
處理 YouTube 比賽影片分析的 API 端點
"""
from flask import request, jsonify
from . import youtube_bp


@youtube_bp.route('/youtube/info', methods=['POST'])
def get_youtube_info():
    """
    取得 YouTube 影片資訊
    
    Request Body:
        { "url": "..." }
    """
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': '請提供 URL'}), 400
            
        from youtube_analyzer import YouTubeDownloader
        downloader = YouTubeDownloader()
        info = downloader.get_video_info(data['url'])
        print(f"Video Info for {data['url']}: {info}", flush=True)
        
        return jsonify(info)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@youtube_bp.route('/youtube/analyze', methods=['POST'])
def analyze_youtube():
    """
    分析 YouTube 桌球比賽影片
    
    Request Body:
        {
            "url": "https://www.youtube.com/watch?v=...",
            "player_focus": "選手名稱（可選）"
        }
    
    Response:
        {
            "success": true,
            "video_info": {...},
            "analysis": {...},
            "record_id": "..."
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': '請提供 YouTube URL'
            }), 400
        
        youtube_url = data['url']
        player_focus = data.get('player_focus')
        player2_focus = data.get('player2_focus')
        description1 = data.get('description1')
        description2 = data.get('description2')
        
        # 驗證 URL
        from services.youtube_service import YouTubeAnalysisService
        from services.history_service import AnalysisHistoryService
        
        service = YouTubeAnalysisService()
        history_service = AnalysisHistoryService()
        
        if not service.validate_url(youtube_url):
            return jsonify({
                'success': False,
                'error': '無效的 YouTube URL'
            }), 400
        
        # 執行分析
        print(f"🎬 開始分析 YouTube 影片: {youtube_url}")
        result = service.analyze(youtube_url, player_focus, player2_focus, description1, description2)
        
        if result['success']:
            # 儲存分析紀錄
            record_id = history_service.save_record(
                video_info=result.get('video_info', {}),
                analysis_result=result.get('analysis', {}),
                player_focus=player_focus,
                player2_focus=player2_focus
            )
            result['record_id'] = record_id
            print(f"✅ 分析紀錄已儲存: {record_id}")
            
            # 儲存選手檔案
            try:
                from services.player_profile_service import get_player_profile_service
                import re
                
                profile_service = get_player_profile_service()
                
                analysis = result.get('analysis', {})
                structured = analysis.get('structured_data') or {}
                sections = analysis.get('sections', {})
                video_info = result.get('video_info', {})
                
                # 如果沒有 player_focus，嘗試從影片標題解析
                p1_name = player_focus
                p2_name = player2_focus
                
                if not p1_name or not p2_name:
                    video_title = video_info.get('title', '')
                    # 嘗試解析 "A VS B" 格式
                    vs_patterns = [
                        r'(.+?)\s+[Vv][Ss]\.?\s+(.+?)(?:\s*[|｜]|$)',
                        r'(.+?)\s+[Vv][Ss]\.?\s+(.+)',
                        r'(.+?)[對対]\s*(.+?)(?:\s*[|｜]|$)',
                    ]
                    for pattern in vs_patterns:
                        match = re.match(pattern, video_title)
                        if match:
                            if not p1_name:
                                p1_name = match.group(1).strip()
                            if not p2_name:
                                p2_name = match.group(2).strip()
                            print(f"📝 從標題解析選手: {p1_name} vs {p2_name}")
                            break
                
                # 儲存選手 1 的檔案
                if p1_name:
                    p1_analysis = structured.get('player1_analysis') or {}
                    profile_service.save_player_analysis(
                        player_name=p1_name,
                        match_id=record_id,
                        video_id=video_info.get('video_id', ''),
                        opponent_name=p2_name or '對手',
                        ratings=p1_analysis.get('ratings', {}),
                        strengths=sections.get('strengths', []),
                        weaknesses=sections.get('weaknesses', [])
                    )
                    print(f"✅ 選手檔案已更新: {p1_name}")
                
                # 儲存選手 2 的檔案
                if p2_name:
                    p2_analysis = structured.get('player2_analysis') or {}
                    profile_service.save_player_analysis(
                        player_name=p2_name,
                        match_id=record_id,
                        video_id=video_info.get('video_id', ''),
                        opponent_name=p1_name or '選手 1',
                        ratings=p2_analysis.get('ratings', {})
                    )
                    print(f"✅ 選手檔案已更新: {p2_name}")
                    
            except Exception as profile_error:
                print(f"⚠️ 選手檔案儲存失敗: {str(profile_error)}")
                import traceback
                traceback.print_exc()
                # 不影響主要流程
            
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        print(f"❌ YouTube 分析失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@youtube_bp.route('/youtube/history', methods=['GET'])
def get_analysis_history():
    """取得分析歷史紀錄列表"""
    try:
        from services.history_service import AnalysisHistoryService
        history_service = AnalysisHistoryService()
        
        limit = request.args.get('limit', 50, type=int)
        player = request.args.get('player')
        search = request.args.get('search')
        
        if player:
            records = history_service.search_records(player)
        elif search:
            records = history_service.search_records(search)
        else:
            records = history_service.get_all_records(limit)
        
        return jsonify({
            'success': True,
            'records': records,
            'total': len(records)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@youtube_bp.route('/youtube/history/<record_id>', methods=['GET'])
def get_analysis_record(record_id: str):
    """取得單一分析紀錄詳情"""
    try:
        from services.history_service import AnalysisHistoryService
        history_service = AnalysisHistoryService()
        
        record = history_service.get_record(record_id)
        
        if record:
            return jsonify({
                'success': True,
                'record': record
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': '找不到該紀錄'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@youtube_bp.route('/youtube/history/<record_id>', methods=['DELETE'])
def delete_analysis_record(record_id: str):
    """刪除分析紀錄"""
    try:
        from services.history_service import AnalysisHistoryService
        history_service = AnalysisHistoryService()
        
        history_service.delete_record(record_id)
        
        return jsonify({
            'success': True,
            'message': '紀錄已刪除'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@youtube_bp.route('/youtube/reclip/<record_id>', methods=['POST'])
def reclip_video(record_id: str):
    """
    重新切割影片片段
    用於已分析過但片段切割失敗的影片
    
    Response:
        {
            "success": true,
            "wins_count": 5,
            "losses_count": 3
        }
    """
    try:
        from services.history_service import AnalysisHistoryService
        from youtube_analyzer import YouTubeDownloader
        import os
        import tempfile
        
        history_service = AnalysisHistoryService()
        
        # 取得分析紀錄
        record = history_service.get_record(record_id)
        if not record:
            return jsonify({
                'success': False,
                'error': '找不到該紀錄'
            }), 404
        
        video_url = record.get('video_url', '')
        video_id = record.get('video_id', '')
        analysis = record.get('analysis_result', {})
        
        if not video_url or not video_id:
            return jsonify({
                'success': False,
                'error': '紀錄中缺少影片資訊'
            }), 400
        
        point_wins = analysis.get('point_wins', [])
        point_losses = analysis.get('point_losses', [])
        
        if not point_wins and not point_losses:
            return jsonify({
                'success': False,
                'error': '紀錄中沒有任何時間戳資訊，請重新分析影片'
            }), 400
        
        print(f"🔄 重新切割片段: {video_id}")
        print(f"  得分片段: {len(point_wins)} 個")
        print(f"  失分片段: {len(point_losses)} 個")
        
        # 下載影片
        downloader = YouTubeDownloader(output_dir=tempfile.gettempdir())
        
        try:
            video_info = downloader.download(video_url)
            video_path = video_info['file_path']
            print(f"📥 影片已下載: {video_path}")
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'影片下載失敗: {str(e)}'
            }), 500
        
        # 定義片段儲存路徑
        base_clip_dir = os.path.join('uploads', 'clips', video_id)
        abs_clip_dir = os.path.abspath(base_clip_dir)
        os.makedirs(abs_clip_dir, exist_ok=True)
        
        # 切割得分片段
        wins_count = 0
        for point in point_wins:
            start = point.get('start_seconds')
            end = point.get('end_seconds')
            point_id = point.get('id', wins_count + 1)
            
            if start is not None and end is not None:
                clip_filename = f"win_{point_id}.mp4"
                clip_path = os.path.join(abs_clip_dir, clip_filename)
                if downloader.cut_local_segment(video_path, start, end, clip_path):
                    point['clip_path'] = f"/uploads/clips/{video_id}/{clip_filename}"
                    wins_count += 1
                    print(f"  ✅ 得分 {point_id}: {start:.1f}s - {end:.1f}s")
        
        # 切割失分片段
        losses_count = 0
        for point in point_losses:
            start = point.get('start_seconds')
            end = point.get('end_seconds')
            point_id = point.get('id', losses_count + 1)
            
            if start is not None and end is not None:
                clip_filename = f"loss_{point_id}.mp4"
                clip_path = os.path.join(abs_clip_dir, clip_filename)
                if downloader.cut_local_segment(video_path, start, end, clip_path):
                    point['clip_path'] = f"/uploads/clips/{video_id}/{clip_filename}"
                    losses_count += 1
                    print(f"  ✅ 失分 {point_id}: {start:.1f}s - {end:.1f}s")
        
        # 清理下載的影片
        try:
            os.remove(video_path)
            print("🧹 已清理暫存影片")
        except:
            pass
        
        # 更新紀錄
        analysis['point_wins'] = point_wins
        analysis['point_losses'] = point_losses
        history_service.save_record(
            video_info={'video_id': video_id, 'url': video_url, 'title': record.get('video_title', ''), 'duration': record.get('video_duration', 0)},
            analysis_result=analysis,
            player_focus=record.get('player_focus'),
            player2_focus=record.get('player2_focus')
        )
        
        print(f"✅ 片段切割完成: 得分 {wins_count} 個, 失分 {losses_count} 個")
        
        return jsonify({
            'success': True,
            'wins_count': wins_count,
            'losses_count': losses_count,
            'message': f'成功切割 {wins_count + losses_count} 個片段'
        }), 200
        
    except Exception as e:
        print(f"❌ 重新切割失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@youtube_bp.route('/youtube/validate', methods=['POST'])
def validate_youtube_url():
    """
    驗證 YouTube URL 是否有效
    
    Request Body:
        {
            "url": "https://www.youtube.com/watch?v=..."
        }
    
    Response:
        {
            "valid": true,
            "video_info": {...}
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({
                'valid': False,
                'error': '請提供 URL'
            }), 400
        
        from services.youtube_service import YouTubeAnalysisService
        service = YouTubeAnalysisService()
        
        is_valid = service.validate_url(data['url'])
        
        response = {'valid': is_valid}
        
        if is_valid:
            try:
                video_info = service.get_video_info(data['url'])
                response['video_info'] = {
                    'title': video_info.get('title'),
                    'duration': video_info.get('duration'),
                    'thumbnail': video_info.get('thumbnail'),
                    'uploader': video_info.get('uploader')
                }
            except:
                pass
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 500


@youtube_bp.route('/youtube/info', methods=['GET'])
def get_analysis_info():
    """取得 YouTube 分析功能資訊"""
    return jsonify({
        'enabled': True,
        'description': '分析 YouTube 桌球比賽影片，識別失分回放並提供改進建議',
        'supported_features': [
            '自動下載 YouTube 影片',
            '使用 Gemini AI 分析比賽',
            '識別失分時刻和原因',
            '提供選手優缺點分析',
            '生成訓練建議'
        ],
        'limitations': {
            'max_duration_minutes': 10,
            'supported_formats': ['youtube.com', 'youtu.be'],
            'requires_yt_dlp': True
        }
    }), 200


@youtube_bp.route('/youtube/analyze-player', methods=['POST'])
def analyze_player_performance():
    """
    分析特定選手的表現（得分+失分+動作品質標註）
    
    Request Body:
        {
            "url": "https://www.youtube.com/watch?v=...",
            "player_name": "選手名稱",
            "player_description": "選手描述（如：穿紅色衣服）"
        }
    
    Response:
        {
            "success": true,
            "player_name": "...",
            "points_won": [...],
            "points_lost": [...],
            "quality_distribution": {...}
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': '請提供 YouTube URL'
            }), 400
        
        if 'player_name' not in data:
            return jsonify({
                'success': False,
                'error': '請提供選手名稱'
            }), 400
        
        youtube_url = data['url']
        player_name = data['player_name']
        player_description = data.get('player_description')
        
        # 驗證 URL
        from services.youtube_service import YouTubeAnalysisService
        service = YouTubeAnalysisService()
        
        if not service.validate_url(youtube_url):
            return jsonify({
                'success': False,
                'error': '無效的 YouTube URL'
            }), 400
        
        # 下載影片
        print(f"🎬 開始分析 {player_name} 的表現: {youtube_url}")
        
        from youtube_analyzer import YouTubeDownloader
        from services.player_analyzer import PlayerPerformanceAnalyzer
        from services.history_service import AnalysisHistoryService
        
        downloader = YouTubeDownloader()
        download_result = downloader.download(youtube_url)
        
        if not download_result.get("success"):
            return jsonify({
                'success': False,
                'error': '影片下載失敗'
            }), 500
        
        # 分析選手表現
        analyzer = PlayerPerformanceAnalyzer()
        result = analyzer.analyze_player_performance(
            download_result["file_path"],
            player_name,
            player_description
        )
        
        # 加入影片資訊
        result["video_info"] = {
            "url": youtube_url,
            "video_id": download_result.get("video_id"),
            "title": download_result.get("title"),
            "duration": download_result.get("duration")
        }
        
        # 儲存分析紀錄
        if result.get("success"):
            history_service = AnalysisHistoryService()
            
            # 將選手分析結果轉換為標準格式儲存
            analysis_result = {
                "raw_analysis": f"選手表現分析：{player_name}",
                "player_analysis": True,
                "match_summary": result.get("match_summary", {}),
                "points_won": result.get("points_won", []),
                "points_lost": result.get("points_lost", []),
                "all_clips": result.get("all_clips", []),
                "quality_distribution": result.get("quality_distribution", {}),
                "training_recommendations": result.get("training_recommendations", [])
            }
            
            # 為了相容性，也設定 point_losses（包含所有片段）
            analysis_result["point_losses"] = result.get("all_clips", [])
            
            record_id = history_service.save_record(
                video_info=result.get("video_info", {}),
                analysis_result=analysis_result,
                player_focus=player_name
            )
            result['record_id'] = record_id
            print(f"✅ 選手分析紀錄已儲存: {record_id}")
        
        # 清理暫存
        try:
            import os
            os.remove(download_result["file_path"])
        except:
            pass
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"❌ 選手分析失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
