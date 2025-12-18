"""
自動訓練 API 路由
"""
from flask import request, jsonify
from services.auto_training_service import get_auto_training_service, ActionLabel
from . import auto_train_bp

@auto_train_bp.route('/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({
        "status": "ok",
        "service": "auto_training"
    })


@auto_train_bp.route('/import', methods=['POST'])
def import_analysis():
    """
    從 YouTube 分析結果匯入訓練片段
    
    Request Body:
        - analysis_result: YouTube 分析結果
        - auto_approve: 是否自動核准 (預設 False)
        - confidence_threshold: 自動核准門檻 (預設 0.7)
    """
    try:
        data = request.get_json()
        analysis_result = data.get('analysis_result')
        auto_approve = data.get('auto_approve', False)
        confidence_threshold = data.get('confidence_threshold', 0.7)
        
        if not analysis_result:
            return jsonify({
                "success": False,
                "error": "請提供分析結果"
            }), 400
        
        service = get_auto_training_service()
        clips = service.import_from_youtube_analysis(
            analysis_result,
            auto_approve=auto_approve,
            confidence_threshold=confidence_threshold
        )
        
        return jsonify({
            "success": True,
            "imported_count": len(clips),
            "clips": [c.to_dict() for c in clips]
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@auto_train_bp.route('/export', methods=['POST'])
def export_clips():
    """
    將已核准的片段匯出到實體訓練資料夾
    """
    try:
        service = get_auto_training_service()
        result = service.export_approved_clips()
        
        return jsonify({
            "success": True,
            "stats": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@auto_train_bp.route('/import-player', methods=['POST'])
def import_player_analysis():
    """
    從選手分析結果匯入訓練片段
    
    Request Body:
        - analysis_result: 選手分析結果 (包含 scoring_clips 和 losing_clips)
        - player_name: 選手名稱
        - auto_approve: 是否自動核准 (預設 True)
        - auto_process: 是否自動處理並匯出 (預設 True)
        - confidence_threshold: 自動核准門檻 (預設 0.7)
    """
    try:
        data = request.get_json()
        analysis_result = data.get('analysis_result')
        player_name = data.get('player_name', '未知選手')
        auto_approve = data.get('auto_approve', True)  # 預設改為 True
        auto_process = data.get('auto_process', True)  # 新增: 預設 True
        confidence_threshold = data.get('confidence_threshold', 0.7)
        
        if not analysis_result:
            return jsonify({
                "success": False,
                "error": "請提供分析結果"
            }), 400
        
        service = get_auto_training_service()
        clips = service.import_from_player_analysis(
            analysis_result,
            player_name=player_name,
            auto_approve=auto_approve,
            auto_process=auto_process,  # 傳入新參數
            confidence_threshold=confidence_threshold
        )
        
        # 統計
        scoring_count = sum(1 for c in clips if '得分' in c.description)
        losing_count = sum(1 for c in clips if '失分' in c.description)
        label_stats = {}
        for c in clips:
            label_stats[c.label] = label_stats.get(c.label, 0) + 1
        
        return jsonify({
            "success": True,
            "imported_count": len(clips),
            "scoring_count": scoring_count,
            "losing_count": losing_count,
            "label_stats": label_stats,
            "auto_processed": auto_process,  # 回傳是否已自動處理
            "clips": [c.to_dict() for c in clips]
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@auto_train_bp.route('/clips', methods=['GET'])
def get_clips():
    """取得片段列表"""
    try:
        status = request.args.get('status')  # pending, approved, rejected, processed
        
        service = get_auto_training_service()
        
        if status == 'pending':
            clips = service.get_pending_clips()
        elif status == 'approved':
            clips = service.get_approved_clips()
        else:
            clips = list(service.clips.values())
        
        return jsonify({
            "success": True,
            "clips": [c.to_dict() for c in clips],
            "count": len(clips)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@auto_train_bp.route('/clips/<clip_id>', methods=['DELETE'])
def delete_clip(clip_id: str):
    """刪除單一片段"""
    try:
        service = get_auto_training_service()
        success = service.delete_clip(clip_id)
        
        if not success:
            return jsonify({
                "success": False,
                "error": "片段不存在"
            }), 404
        
        return jsonify({
            "success": True,
            "message": "片段已刪除"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@auto_train_bp.route('/clips', methods=['DELETE'])
def clear_all_clips():
    """清空所有片段"""
    try:
        service = get_auto_training_service()
        count = service.clear_all_clips()
        
        return jsonify({
            "success": True,
            "message": f"已清空 {count} 個片段",
            "count": count
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@auto_train_bp.route('/clips/<clip_id>', methods=['GET'])
def get_clip(clip_id: str):
    """取得單一片段"""
    try:
        service = get_auto_training_service()
        
        if clip_id not in service.clips:
            return jsonify({
                "success": False,
                "error": "片段不存在"
            }), 404
        
        return jsonify({
            "success": True,
            "clip": service.clips[clip_id].to_dict()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@auto_train_bp.route('/clips/<clip_id>/approve', methods=['POST'])
def approve_clip(clip_id: str):
    """核准片段"""
    try:
        data = request.get_json() or {}
        label = data.get('label')  # 可選，修改標籤
        
        service = get_auto_training_service()
        success = service.approve_clip(clip_id, label)
        
        if not success:
            return jsonify({
                "success": False,
                "error": "片段不存在"
            }), 404
        
        return jsonify({
            "success": True,
            "clip": service.clips[clip_id].to_dict()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@auto_train_bp.route('/clips/<clip_id>/reject', methods=['POST'])
def reject_clip(clip_id: str):
    """拒絕片段"""
    try:
        service = get_auto_training_service()
        success = service.reject_clip(clip_id)
        
        if not success:
            return jsonify({
                "success": False,
                "error": "片段不存在"
            }), 404
        
        return jsonify({
            "success": True,
            "message": "片段已拒絕"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@auto_train_bp.route('/clips/<clip_id>/label', methods=['PUT'])
def update_label(clip_id: str):
    """更新片段標籤"""
    try:
        data = request.get_json()
        label = data.get('label')
        
        if not label:
            return jsonify({
                "success": False,
                "error": "請提供標籤"
            }), 400
        
        valid_labels = [l.value for l in ActionLabel]
        if label not in valid_labels:
            return jsonify({
                "success": False,
                "error": f"無效的標籤，可用: {valid_labels}"
            }), 400
        
        service = get_auto_training_service()
        success = service.update_clip_label(clip_id, label)
        
        if not success:
            return jsonify({
                "success": False,
                "error": "片段不存在"
            }), 404
        
        return jsonify({
            "success": True,
            "clip": service.clips[clip_id].to_dict()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@auto_train_bp.route('/clips/<clip_id>/process', methods=['POST'])
def process_clip(clip_id: str):
    """處理片段（下載 + 骨架提取）"""
    try:
        service = get_auto_training_service()
        
        if clip_id not in service.clips:
            return jsonify({
                "success": False,
                "error": "片段不存在"
            }), 404
        
        clip = service.clips[clip_id]
        
        if clip.status not in ['approved', 'pending']:
            return jsonify({
                "success": False,
                "error": f"片段狀態 ({clip.status}) 無法處理"
            }), 400
        
        # 下載片段
        video_path = service.download_and_extract_clip(clip_id)
        if not video_path:
            return jsonify({
                "success": False,
                "error": "下載片段失敗"
            }), 500
        
        # 提取骨架
        skeleton_path = service.extract_skeleton(clip_id)
        if not skeleton_path:
            return jsonify({
                "success": False,
                "error": "骨架提取失敗",
                "video_downloaded": True
            }), 500
        
        return jsonify({
            "success": True,
            "clip": service.clips[clip_id].to_dict(),
            "video_path": video_path,
            "skeleton_path": skeleton_path
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@auto_train_bp.route('/process-all', methods=['POST'])
def process_all_approved():
    """處理所有已核准的片段"""
    try:
        service = get_auto_training_service()
        approved = service.get_approved_clips()
        
        results = {
            "total": len(approved),
            "success": 0,
            "failed": 0,
            "details": []
        }
        
        for clip in approved:
            try:
                video_path = service.download_and_extract_clip(clip.clip_id)
                if video_path:
                    skeleton_path = service.extract_skeleton(clip.clip_id)
                    if skeleton_path:
                        results["success"] += 1
                        results["details"].append({
                            "clip_id": clip.clip_id,
                            "status": "success"
                        })
                        continue
                
                results["failed"] += 1
                results["details"].append({
                    "clip_id": clip.clip_id,
                    "status": "failed"
                })
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "clip_id": clip.clip_id,
                    "status": "error",
                    "message": str(e)
                })
        
        return jsonify({
            "success": True,
            **results
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@auto_train_bp.route('/copy-to-training', methods=['POST'])
def copy_to_training():
    """複製處理完成的資料到訓練資料夾"""
    try:
        service = get_auto_training_service()
        counts = service.copy_to_training_folder()
        
        return jsonify({
            "success": True,
            "copied": counts,
            "total": sum(counts.values())
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@auto_train_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """取得統計資訊"""
    try:
        service = get_auto_training_service()
        stats = service.get_statistics()
        
        return jsonify({
            "success": True,
            "statistics": stats
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@auto_train_bp.route('/training-batch', methods=['GET'])
def get_training_batch():
    """取得訓練批次資料"""
    try:
        label = request.args.get('label')
        
        service = get_auto_training_service()
        batch = service.prepare_training_batch(label)
        
        return jsonify({
            "success": True,
            "batch": batch
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
