'use client';

import { useState, useEffect } from 'react';

interface TrainingStats {
  simple: {
    total: number;
    by_class: Record<string, number>;
    ready_for_training: boolean;
  };
  technique: {
    total: number;
    by_class: Record<string, number>;
    ready_for_training: boolean;
  };
}

interface TrainingProgress {
  status: string;
  message: string;
  current_epoch: number;
  total_epochs: number;
  accuracy?: number;
  val_accuracy?: number;
  loss?: number;
  val_loss?: number;
  logs: string[];
}

interface TrainingResult {
  success: boolean;
  accuracy: number;
  val_accuracy: number;
  loss: number;
  val_loss: number;
  training_time: string;
  total_samples: number;
  num_classes: number;
  class_names: string[];
  per_class_accuracy?: Record<string, number>;
  model_path?: string;
}

interface ModelInfo {
  filename: string;
  mode: string;
  architecture: string;
  accuracy: number;
  created_at: string;
  class_names: string[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

const TECHNIQUE_CLASS_NAMES: Record<string, string> = {
  'forehand_attack': '正手進攻', 'backhand_attack': '反手進攻',
  'smash': '扣殺', 'loop_drive': '弧圈球',
  'block': '擋球', 'chop': '削球', 'lob': '挑球',
  'serve_ace': '發球直接得分', 'serve_attack': '發球搶攻',
  'receive_attack': '接發搶攻', 'receive_control': '接發控制',
  'forehand_error': '正手失誤', 'backhand_error': '反手失誤',
  'serve_error': '發球失誤', 'receive_error': '接發失誤',
  'net_error': '下網', 'out_of_bounds': '出界',
  'footwork_error': '步法失誤', 'judgment_error': '判斷失誤',
  'other': '其他'
};

export default function UnifiedTrainingPanel() {
  // 訓練模式
  const [mode, setMode] = useState<'simple' | 'technique'>('simple');
  const [architecture, setArchitecture] = useState('bidirectional');
  
  // 訓練配置
  const [epochs, setEpochs] = useState(80);
  const [batchSize, setBatchSize] = useState(32);
  const [learningRate, setLearningRate] = useState(0.001);
  const [useAugmentation, setUseAugmentation] = useState(true);
  const [augmentFactor, setAugmentFactor] = useState(3);
  
  // 狀態
  const [stats, setStats] = useState<TrainingStats | null>(null);
  const [isTraining, setIsTraining] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState<TrainingProgress | null>(null);
  const [result, setResult] = useState<TrainingResult | null>(null);
  const [error, setError] = useState('');
  const [models, setModels] = useState<ModelInfo[]>([]);
  
  // 載入統計資料
  useEffect(() => {
    fetchStats();
    fetchModels();
  }, []);
  
  // 輪詢訓練狀態
  useEffect(() => {
    if (!taskId || !isTraining) return;
    
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/api/unified-training/train/status/${taskId}`);
        const data = await res.json();
        
        if (data.success) {
          setProgress({
            status: data.status,
            message: data.message,
            current_epoch: data.current_epoch,
            total_epochs: data.total_epochs,
            accuracy: data.accuracy,
            val_accuracy: data.val_accuracy,
            loss: data.loss,
            val_loss: data.val_loss,
            logs: data.logs || []
          });
          
          if (data.status === 'completed') {
            setIsTraining(false);
            setResult(data.result);
            fetchModels();
          } else if (data.status === 'failed') {
            setIsTraining(false);
            setError(data.message || '訓練失敗');
          }
        }
      } catch (err) {
        console.error('輪詢狀態錯誤:', err);
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, [taskId, isTraining]);
  
  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/unified-training/stats`);
      const data = await res.json();
      if (data.success) {
        setStats(data.stats);
      }
    } catch (err) {
      console.error('載入統計資料失敗:', err);
    }
  };
  
  const fetchModels = async () => {
    try {
      const res = await fetch(`${API_URL}/api/unified-training/models`);
      const data = await res.json();
      if (data.success) {
        setModels(data.models);
      }
    } catch (err) {
      console.error('載入模型列表失敗:', err);
    }
  };
  
  const handleStartTraining = async () => {
    setIsTraining(true);
    setError('');
    setResult(null);
    setProgress(null);
    
    try {
      const res = await fetch(`${API_URL}/api/unified-training/train`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode,
          architecture,
          epochs,
          batch_size: batchSize,
          learning_rate: learningRate,
          use_augmentation: useAugmentation,
          augment_factor: augmentFactor,
          use_class_weights: true
        })
      });
      
      const data = await res.json();
      
      if (data.success) {
        setTaskId(data.task_id);
      } else {
        setError(data.error || '訓練啟動失敗');
        setIsTraining(false);
      }
    } catch (err: any) {
      setError(err.message || '訓練啟動失敗');
      setIsTraining(false);
    }
  };
  
  const handleQuickTrain = async () => {
    setIsTraining(true);
    setError('');
    setResult(null);
    setProgress(null);
    
    try {
      const res = await fetch(`${API_URL}/api/unified-training/quick-train`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode })
      });
      
      const data = await res.json();
      
      if (data.success) {
        setTaskId(data.task_id);
      } else {
        setError(data.error || '快速訓練啟動失敗');
        setIsTraining(false);
      }
    } catch (err: any) {
      setError(err.message || '快速訓練啟動失敗');
      setIsTraining(false);
    }
  };
  
  const handleDeleteModel = async (filename: string) => {
    if (!confirm('確定要刪除此模型嗎？')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/unified-training/models/${filename}`, {
        method: 'DELETE'
      });
      
      if (res.ok) {
        fetchModels();
      }
    } catch (err) {
      console.error('刪除模型失敗:', err);
    }
  };
  
  const getProgressPercentage = () => {
    if (!progress?.current_epoch || !progress?.total_epochs) return 0;
    return (progress.current_epoch / progress.total_epochs) * 100;
  };
  
  const currentStats = mode === 'simple' ? stats?.simple : stats?.technique;
  
  return (
    <div className="space-y-6">
      {/* 訓練模式選擇 */}
      <div className="bg-white rounded-2xl border border-neutral-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-neutral-900 mb-4">選擇訓練模式</h2>
        
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={() => setMode('simple')}
            disabled={isTraining}
            className={`p-4 rounded-xl border-2 transition-all ${
              mode === 'simple'
                ? 'border-neutral-900 bg-neutral-50'
                : 'border-neutral-200 hover:border-neutral-300'
            } ${isTraining ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <div className="text-2xl mb-2">📊</div>
            <div className="font-medium text-neutral-900">簡單分類</div>
            <div className="text-xs text-neutral-500 mt-1">
              Good / Normal / Bad 三分類
            </div>
            {stats?.simple && (
              <div className="mt-2 text-xs text-neutral-600">
                資料: {stats.simple.total} 個樣本
              </div>
            )}
          </button>
          
          <button
            onClick={() => setMode('technique')}
            disabled={isTraining}
            className={`p-4 rounded-xl border-2 transition-all ${
              mode === 'technique'
                ? 'border-neutral-900 bg-neutral-50'
                : 'border-neutral-200 hover:border-neutral-300'
            } ${isTraining ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <div className="text-2xl mb-2">🎯</div>
            <div className="font-medium text-neutral-900">技術分類</div>
            <div className="text-xs text-neutral-500 mt-1">
              20 種技術類型分類
            </div>
            {stats?.technique && (
              <div className="mt-2 text-xs text-neutral-600">
                資料: {stats.technique.total} 個樣本
              </div>
            )}
          </button>
        </div>
      </div>
      
      {/* 資料統計 */}
      {currentStats && (
        <div className="bg-white rounded-2xl border border-neutral-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">
            訓練資料統計
            <span className={`ml-2 text-sm font-normal ${
              currentStats.ready_for_training ? 'text-green-600' : 'text-orange-600'
            }`}>
              {currentStats.ready_for_training ? '✓ 可訓練' : '⚠ 資料不足'}
            </span>
          </h2>
          
          <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
            {Object.entries(currentStats.by_class).map(([className, count]) => (
              <div key={className} className="bg-neutral-50 rounded-lg p-3 text-center">
                <div className="text-xs text-neutral-500 truncate">
                  {mode === 'simple' 
                    ? (className === 'good' ? '得分' : className === 'bad' ? '失誤' : '一般')
                    : (TECHNIQUE_CLASS_NAMES[className] || className)
                  }
                </div>
                <div className="text-lg font-semibold text-neutral-900">{count}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* 訓練配置 */}
      <div className="bg-white rounded-2xl border border-neutral-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-neutral-900 mb-4">訓練配置</h2>
        
        <div className="grid grid-cols-2 gap-4">
          {/* 模型架構 */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              模型架構
            </label>
            <select
              value={architecture}
              onChange={(e) => setArchitecture(e.target.value)}
              disabled={isTraining}
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm disabled:opacity-50"
            >
              <option value="basic">Basic LSTM</option>
              <option value="bidirectional">雙向 LSTM (推薦)</option>
              <option value="deep">深層 LSTM</option>
              <option value="advanced">進階模型</option>
            </select>
          </div>
          
          {/* 訓練輪數 */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              訓練輪數: {epochs}
            </label>
            <input
              type="range"
              min="20"
              max="200"
              step="10"
              value={epochs}
              onChange={(e) => setEpochs(parseInt(e.target.value))}
              disabled={isTraining}
              className="w-full"
            />
          </div>
          
          {/* 批次大小 */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              批次大小
            </label>
            <select
              value={batchSize}
              onChange={(e) => setBatchSize(parseInt(e.target.value))}
              disabled={isTraining}
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm disabled:opacity-50"
            >
              <option value="16">16</option>
              <option value="32">32</option>
              <option value="64">64</option>
            </select>
          </div>
          
          {/* 學習率 */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              學習率
            </label>
            <select
              value={learningRate}
              onChange={(e) => setLearningRate(parseFloat(e.target.value))}
              disabled={isTraining}
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm disabled:opacity-50"
            >
              <option value="0.0001">0.0001</option>
              <option value="0.001">0.001 (推薦)</option>
              <option value="0.01">0.01</option>
            </select>
          </div>
        </div>
        
        {/* 資料增強 */}
        <div className="mt-4 pt-4 border-t border-neutral-100">
          <label className="flex items-center justify-between">
            <span className="text-sm font-medium text-neutral-700">資料增強</span>
            <input
              type="checkbox"
              checked={useAugmentation}
              onChange={(e) => setUseAugmentation(e.target.checked)}
              disabled={isTraining}
              className="w-4 h-4"
            />
          </label>
          
          {useAugmentation && (
            <div className="mt-3">
              <label className="block text-sm text-neutral-600 mb-1">
                增強倍數: {augmentFactor}x
              </label>
              <input
                type="range"
                min="1"
                max="5"
                value={augmentFactor}
                onChange={(e) => setAugmentFactor(parseInt(e.target.value))}
                disabled={isTraining}
                className="w-full"
              />
            </div>
          )}
        </div>
        
        {/* 訓練按鈕 */}
        <div className="mt-6 flex gap-3">
          <button
            onClick={handleQuickTrain}
            disabled={isTraining || !currentStats?.ready_for_training}
            className="flex-1 px-4 py-3 bg-neutral-100 text-neutral-900 rounded-xl font-medium transition-all hover:bg-neutral-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ⚡ 一鍵快速訓練
          </button>
          
          <button
            onClick={handleStartTraining}
            disabled={isTraining || !currentStats?.ready_for_training}
            className="flex-1 px-4 py-3 bg-neutral-900 text-white rounded-xl font-medium transition-all hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isTraining ? '訓練中...' : '🚀 開始訓練'}
          </button>
        </div>
      </div>
      
      {/* 訓練進度 */}
      {(isTraining || progress) && (
        <div className="bg-white rounded-2xl border border-neutral-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">訓練進度</h2>
          
          {progress && (
            <>
              {/* 進度條 */}
              <div className="mb-4">
                <div className="flex justify-between text-sm mb-1">
                  <span>Epoch {progress.current_epoch} / {progress.total_epochs}</span>
                  <span>{getProgressPercentage().toFixed(0)}%</span>
                </div>
                <div className="bg-neutral-100 rounded-full h-2 overflow-hidden">
                  <div 
                    className="bg-neutral-900 h-full transition-all"
                    style={{ width: `${getProgressPercentage()}%` }}
                  />
                </div>
              </div>
              
              {/* 指標 */}
              <div className="grid grid-cols-4 gap-3 mb-4">
                {progress.accuracy !== undefined && (
                  <div className="bg-neutral-50 rounded-lg p-3 text-center">
                    <div className="text-xs text-neutral-500">準確率</div>
                    <div className="text-lg font-semibold">{(progress.accuracy * 100).toFixed(1)}%</div>
                  </div>
                )}
                {progress.val_accuracy !== undefined && (
                  <div className="bg-neutral-50 rounded-lg p-3 text-center">
                    <div className="text-xs text-neutral-500">驗證準確率</div>
                    <div className="text-lg font-semibold">{(progress.val_accuracy * 100).toFixed(1)}%</div>
                  </div>
                )}
                {progress.loss !== undefined && (
                  <div className="bg-neutral-50 rounded-lg p-3 text-center">
                    <div className="text-xs text-neutral-500">損失</div>
                    <div className="text-lg font-semibold">{progress.loss.toFixed(4)}</div>
                  </div>
                )}
                {progress.val_loss !== undefined && (
                  <div className="bg-neutral-50 rounded-lg p-3 text-center">
                    <div className="text-xs text-neutral-500">驗證損失</div>
                    <div className="text-lg font-semibold">{progress.val_loss.toFixed(4)}</div>
                  </div>
                )}
              </div>
              
              {/* 日誌 */}
              {progress.logs.length > 0 && (
                <div className="bg-neutral-900 rounded-lg p-3 h-40 overflow-y-auto font-mono text-xs">
                  {progress.logs.slice(-15).map((log, i) => (
                    <div key={i} className="text-neutral-300">{log}</div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
      
      {/* 錯誤訊息 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-4">
          <div className="text-red-800 font-medium">錯誤</div>
          <div className="text-red-600 text-sm mt-1">{error}</div>
        </div>
      )}
      
      {/* 訓練結果 */}
      {result && (
        <div className="bg-green-50 border border-green-200 rounded-2xl p-6">
          <div className="text-center mb-4">
            <div className="text-4xl mb-2">🎉</div>
            <div className="text-xl font-semibold text-green-800">訓練完成！</div>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-white rounded-lg p-3 text-center">
              <div className="text-xs text-neutral-500">測試準確率</div>
              <div className="text-xl font-semibold text-green-700">
                {(result.accuracy * 100).toFixed(1)}%
              </div>
            </div>
            <div className="bg-white rounded-lg p-3 text-center">
              <div className="text-xs text-neutral-500">類別數</div>
              <div className="text-xl font-semibold">{result.num_classes}</div>
            </div>
            <div className="bg-white rounded-lg p-3 text-center">
              <div className="text-xs text-neutral-500">樣本數</div>
              <div className="text-xl font-semibold">{result.total_samples}</div>
            </div>
            <div className="bg-white rounded-lg p-3 text-center">
              <div className="text-xs text-neutral-500">訓練時間</div>
              <div className="text-xl font-semibold">{result.training_time}</div>
            </div>
          </div>
          
          {result.per_class_accuracy && (
            <div className="mt-4">
              <div className="text-sm font-medium text-neutral-700 mb-2">各類別準確率</div>
              <div className="grid grid-cols-3 gap-2">
                {Object.entries(result.per_class_accuracy).map(([className, acc]) => (
                  <div key={className} className="bg-white rounded-lg p-2 text-center text-sm">
                    <div className="text-neutral-600 truncate">{className}</div>
                    <div className="font-medium">{((acc as number) * 100).toFixed(1)}%</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* 模型列表 */}
      {models.length > 0 && (
        <div className="bg-white rounded-2xl border border-neutral-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">已訓練模型</h2>
          
          <div className="space-y-2">
            {models.map((model) => (
              <div 
                key={model.filename}
                className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg"
              >
                <div>
                  <div className="font-medium text-neutral-900">{model.filename}</div>
                  <div className="text-xs text-neutral-500">
                    {model.mode} • {model.architecture} • 準確率: {((model.accuracy || 0) * 100).toFixed(1)}%
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteModel(model.filename)}
                  className="text-red-500 hover:text-red-700 text-sm"
                >
                  刪除
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
