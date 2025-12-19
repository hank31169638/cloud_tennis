"""测试导入"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing imports...")
    
    # 测试统一训练服务
    from services.unified_training_service import get_unified_training_service, TrainingConfig
    print("✅ unified_training_service imported successfully")
    
    # 测试增强预测服务
    from services.enhanced_prediction_service import get_enhanced_prediction_service
    print("✅ enhanced_prediction_service imported successfully")
    
    # 测试统一训练路由
    from routes.unified_training_routes import unified_training_bp
    print("✅ unified_training_routes imported successfully")
    print(f"   Blueprint name: {unified_training_bp.name}")
    print(f"   URL prefix: {unified_training_bp.url_prefix}")
    
    # 测试获取统计
    service = get_unified_training_service()
    stats = service.get_training_data_stats()
    print("\n📊 Training Data Stats:")
    print(f"   Simple mode: {stats['simple']['total']} samples")
    print(f"   Technique mode: {stats['technique']['total']} samples")
    
    print("\n🎉 All imports successful!")
    
except Exception as e:
    import traceback
    print(f"❌ Error: {e}")
    traceback.print_exc()
