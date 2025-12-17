"""
失誤分析系統測試腳本
測試 Gemini AI 整合和影片分析功能
"""
import os
import sys
import json
from pathlib import Path

# 添加專案路徑
sys.path.insert(0, os.path.dirname(__file__))

def test_basic_imports():
    """測試基本模組導入"""
    print("🧪 測試 1: 基本模組導入")
    print("-" * 50)
    
    try:
        import cv2
        print("✅ OpenCV 已安裝:", cv2.__version__)
    except ImportError as e:
        print(f"❌ OpenCV 未安裝: {e}")
        return False
    
    try:
        import google.generativeai as genai
        print("✅ Google Generative AI 已安裝")
    except ImportError as e:
        print(f"⚠️  Google Generative AI 未安裝: {e}")
        print("   提示: pip install google-generativeai")
    
    
    print()
    return True


def test_gemini_connection():
    """測試 Gemini API 連接"""
    print("🧪 測試 2: Gemini API 連接")
    print("-" * 50)
    
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print("⚠️  未設定 GEMINI_API_KEY 環境變數")
        print("   提示: 請在 .env 檔案中設定 GEMINI_API_KEY")
        print("   或執行: export GEMINI_API_KEY=your_api_key")
        return False
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # 測試簡單的文字生成
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content("Say hello in Traditional Chinese")
        
        print(f"✅ Gemini API 連接成功")
        print(f"   測試回應: {response.text[:50]}...")
        print()
        return True
    
    except Exception as e:
        print(f"❌ Gemini API 連接失敗: {e}")
        print()
        return False


def test_failure_analyzer():
    """測試失誤分析器"""
    print("🧪 測試 3: 失誤分析器初始化")
    print("-" * 50)
    
    try:
        from failure_analyzer import FailureAnalyzer
        
        analyzer = FailureAnalyzer()
        print("✅ FailureAnalyzer 初始化成功")
        
        # 檢查 Gemini 是否可用
        if analyzer.model:
            print("✅ Gemini AI 已啟用")
        else:
            print("⚠️  Gemini AI 未啟用（將使用基礎分析模式）")
        
        print()
        return True
    
    except Exception as e:
        print(f"❌ FailureAnalyzer 初始化失敗: {e}")
        print()
        return False


def test_video_analysis(video_path=None):
    """測試影片分析"""
    print("🧪 測試 4: 影片分析")
    print("-" * 50)
    
    if not video_path:
        print("⚠️  未提供測試影片路徑，跳過此測試")
        print("   提示: python test_failure_analyzer.py <video_path>")
        print()
        return True
    
    if not os.path.exists(video_path):
        print(f"❌ 影片檔案不存在: {video_path}")
        print()
        return False
    
    try:
        from failure_analyzer import FailureAnalyzer
        
        analyzer = FailureAnalyzer()
        print(f"📹 分析影片: {video_path}")
        print()
        
        # 執行分析
        result = analyzer.analyze_failure(video_path, use_gemini=True)
        
        print("✅ 分析完成！")
        print()
        print("=" * 50)
        print("分析結果：")
        print("=" * 50)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        # 儲存結果
        output_path = video_path.replace('.mp4', '_analysis.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"📄 分析結果已儲存至: {output_path}")
        print()
        return True
    
    except Exception as e:
        print(f"❌ 影片分析失敗: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_structured_data_generation(video_path=None):
    """測試結構化數據生成"""
    print("🧪 測試 5: 結構化數據生成")
    print("-" * 50)
    
    if not video_path:
        print("⚠️  未提供測試影片路徑，跳過此測試")
        print()
        return True
    
    if not os.path.exists(video_path):
        print(f"❌ 影片檔案不存在: {video_path}")
        print()
        return False
    
    try:
        from failure_analyzer import FailureAnalyzer
        
        analyzer = FailureAnalyzer()
        print(f"📊 生成結構化數據: {video_path}")
        
        structured_data = analyzer.generate_structured_analysis(video_path)
        
        print("✅ 結構化數據生成成功！")
        print()
        print("數據摘要：")
        print(f"  - 影片時長: {structured_data['video_info']['duration_seconds']:.2f} 秒")
        print(f"  - 分析幀數: {structured_data['video_info']['analyzed_frames']}")
        print(f"  - 姿態數據: {structured_data['pose_analysis']['analyzed_frames']} 幀")
        print(f"  - 平均拍面角度: {structured_data['pose_analysis']['avg_racket_angle']:.1f}°")
        print(f"  - 拍面角度變異: {structured_data['pose_analysis']['racket_angle_variance']:.1f}")
        print()
        print("技術指標：")
        for key, value in structured_data['technical_indicators'].items():
            print(f"  - {key}: {value}")
        print()
        
        return True
    
    except Exception as e:
        print(f"❌ 結構化數據生成失敗: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def main():
    """執行所有測試"""
    print()
    print("="*60)
    print("      失誤分析系統測試")
    print("="*60)
    print()
    
    # 檢查是否有提供影片路徑
    video_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # 執行測試
    tests = [
        ("基本模組導入", test_basic_imports),
        ("Gemini API 連接", test_gemini_connection),
        ("失誤分析器初始化", test_failure_analyzer),
        ("結構化數據生成", lambda: test_structured_data_generation(video_path)),
        ("完整影片分析", lambda: test_video_analysis(video_path))
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 測試異常: {test_name}")
            print(f"   錯誤: {e}")
            results.append((test_name, False))
    
    # 顯示測試摘要
    print()
    print("="*60)
    print("測試摘要")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{status}: {test_name}")
    
    print()
    print(f"總計: {passed}/{total} 通過")
    print("="*60)
    print()
    
    # 提示如何使用
    if not video_path:
        print("💡 提示：")
        print("   若要測試完整分析功能，請提供影片路徑：")
        print("   python test_failure_analyzer.py <video_path>")
        print()


if __name__ == '__main__':
    main()
