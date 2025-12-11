'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import Navbar from '../components/Navbar';
import { io, Socket } from 'socket.io-client';

interface Alert {
  id: string;
  timestamp: number;
  alert_type: 'info' | 'warning' | 'critical' | 'success' | 'tactic';
  title: string;
  message: string;
  suggestion?: string;
}

interface MatchState {
  player1_score: number;
  player2_score: number;
  current_set: number;
  consecutive_errors: number;
  weakness_detected: string[];
}

export default function LiveAnalysisPage() {
  const [isConnected, setIsConnected] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [playerFocus, setPlayerFocus] = useState('');
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [matchState, setMatchState] = useState<MatchState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [enablePose, setEnablePose] = useState(true);
  const [poseLoaded, setPoseLoaded] = useState(false);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const socketRef = useRef<Socket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const frameIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const poseDetectionRef = useRef<NodeJS.Timeout | null>(null);
  const poseRef = useRef<any>(null);
  
  const alertsEndRef = useRef<HTMLDivElement>(null);
  const drawingUtilsRef = useRef<any>(null);
  const poseConnectionsRef = useRef<any>(null);
  
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
  const wsUrl = apiUrl.replace('http', 'ws');

  // 自動滾動到最新提醒
  useEffect(() => {
    alertsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [alerts]);

  // 初始化 MediaPipe Pose (前端)
  useEffect(() => {
    const loadMediaPipe = async () => {
      try {
        // 動態載入 MediaPipe
        const poseModule = await import('@mediapipe/pose');
        const drawingModule = await import('@mediapipe/drawing_utils');
        
        const { Pose, POSE_CONNECTIONS } = poseModule;
        const { drawConnectors, drawLandmarks } = drawingModule;
        
        // 保存引用
        poseConnectionsRef.current = POSE_CONNECTIONS;
        drawingUtilsRef.current = { drawConnectors, drawLandmarks };
        
        const pose = new Pose({
          locateFile: (file: string) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
          }
        });
        
        pose.setOptions({
          modelComplexity: 1,
          smoothLandmarks: true,
          enableSegmentation: false,
          minDetectionConfidence: 0.5,
          minTrackingConfidence: 0.5
        });
        
        pose.onResults((results: any) => {
          if (!overlayCanvasRef.current || !videoRef.current) return;
          
          const canvas = overlayCanvasRef.current;
          const ctx = canvas.getContext('2d');
          if (!ctx) return;
          
          // 設置 canvas 尺寸與視訊相同
          const videoWidth = videoRef.current.videoWidth || 640;
          const videoHeight = videoRef.current.videoHeight || 480;
          
          if (canvas.width !== videoWidth || canvas.height !== videoHeight) {
            canvas.width = videoWidth;
            canvas.height = videoHeight;
          }
          
          // 清除 canvas
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          
          // 繪製骨架
          if (results.poseLandmarks && drawingUtilsRef.current && poseConnectionsRef.current) {
            const { drawConnectors: dc, drawLandmarks: dl } = drawingUtilsRef.current;
            
            dc(ctx, results.poseLandmarks, poseConnectionsRef.current, {
              color: '#00FF00',
              lineWidth: 4
            });
            dl(ctx, results.poseLandmarks, {
              color: '#FF0000',
              lineWidth: 2,
              radius: 6
            });
          }
        });
        
        await pose.initialize();
        poseRef.current = pose;
        setPoseLoaded(true);
        console.log('✅ MediaPipe Pose 已載入');
      } catch (err) {
        console.error('❌ MediaPipe Pose 載入失敗:', err);
        setError('骨架偵測載入失敗: ' + (err as Error).message);
      }
    };
    
    if (enablePose && !poseLoaded) {
      loadMediaPipe();
    }
  }, [enablePose, poseLoaded]);

  // 即時骨架偵測
  useEffect(() => {
    if (!enablePose || !poseLoaded || !isAnalyzing || !poseRef.current) {
      return;
    }
    
    const detectPose = async () => {
      if (videoRef.current && poseRef.current && videoRef.current.readyState >= 2) {
        try {
          await poseRef.current.send({ image: videoRef.current });
        } catch (err) {
          // 忽略偵測錯誤，避免過多 console 輸出
        }
      }
    };
    
    // 每 66ms 偵測一次 (約 15 FPS)
    poseDetectionRef.current = setInterval(detectPose, 66);
    console.log('🦴 開始即時骨架偵測');
    
    return () => {
      if (poseDetectionRef.current) {
        clearInterval(poseDetectionRef.current);
        console.log('⏹️ 停止骨架偵測');
      }
    };
  }, [enablePose, poseLoaded, isAnalyzing]);

  // 初始化攝影機
  const initCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'environment'
        },
        audio: false
      });
      
      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      
      setCameraError(null);
      return true;
    } catch (err) {
      console.error('攝影機錯誤:', err);
      setCameraError('無法存取攝影機，請確認權限設定');
      return false;
    }
  };

  // 停止攝影機
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  };

  // 連接 Socket.IO
  const connectWebSocket = () => {
    const socket = io(apiUrl, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });
    
    // 連接到 /live namespace
    const liveSocket = io(`${apiUrl}/live`, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
    });
    
    liveSocket.on('connect', () => {
      console.log('✅ Socket.IO 已連接');
      setIsConnected(true);
      setError(null);
    });
    
    liveSocket.on('disconnect', () => {
      console.log('❌ Socket.IO 已斷開');
      setIsConnected(false);
    });
    
    liveSocket.on('connect_error', (err) => {
      console.error('Socket.IO 連接錯誤:', err);
      setError('連接失敗: ' + err.message);
    });
    
    // 監聽事件
    liveSocket.on('alert', (data) => {
      setAlerts(prev => [...prev.slice(-49), data]);
      playAlertSound(data.alert_type);
    });
    
    liveSocket.on('analysis_started', () => {
      console.log('✅ 分析已開始');
      setIsAnalyzing(true);
    });
    
    liveSocket.on('analysis_stopped', () => {
      console.log('⏹️ 分析已停止');
      setIsAnalyzing(false);
    });
    
    liveSocket.on('state', (data) => {
      setMatchState(data.match_state);
    });
    
    liveSocket.on('error', (data) => {
      setError(data.message);
    });
    
    liveSocket.on('prediction', (data) => {
      console.log('🎯 收到預測:', data);
    });
    
    socketRef.current = liveSocket;
  };

  // 播放提示音
  const playAlertSound = (type: string) => {
    // 使用 Web Audio API 播放簡單提示音
    try {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      // 根據類型設定不同音調
      switch (type) {
        case 'critical':
          oscillator.frequency.value = 800;
          oscillator.type = 'square';
          break;
        case 'warning':
          oscillator.frequency.value = 600;
          oscillator.type = 'triangle';
          break;
        case 'success':
          oscillator.frequency.value = 1000;
          oscillator.type = 'sine';
          break;
        default:
          oscillator.frequency.value = 440;
          oscillator.type = 'sine';
      }
      
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.3);
    } catch (e) {
      // 忽略音效錯誤
    }
  };

  // 開始分析
  const startAnalysis = async () => {
    // 初始化攝影機
    const cameraReady = await initCamera();
    if (!cameraReady) return;
    
    // 連接 Socket.IO
    if (!socketRef.current || !socketRef.current.connected) {
      connectWebSocket();
      // 等待連接
      await new Promise(resolve => setTimeout(resolve, 1500));
    }
    
    // 發送開始分析事件
    if (socketRef.current && socketRef.current.connected) {
      socketRef.current.emit('start_analysis', { player_focus: playerFocus || null });
      setIsAnalyzing(true);
      
      // 開始發送視訊幀
      startFrameCapture();
    } else {
      setError('無法連接到伺服器');
    }
  };

  // 開始擷取視訊幀
  const startFrameCapture = () => {
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
    }
    
    frameIntervalRef.current = setInterval(() => {
      captureAndSendFrame();
    }, 1000); // 每秒擷取一幀
  };

  // 擷取並發送視訊幀
  const captureAndSendFrame = () => {
    if (!videoRef.current || !canvasRef.current || !socketRef.current) return;
    if (!socketRef.current.connected) return;
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    if (!ctx) return;
    
    // 設定 canvas 大小
    canvas.width = 640;
    canvas.height = 360;
    
    // 繪製視訊幀
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // 轉換為 base64
    const frameData = canvas.toDataURL('image/jpeg', 0.7).split(',')[1];
    
    // 使用 Socket.IO emit 發送幀
    socketRef.current.emit('video_frame', { 
      frame: frameData,
      enable_pose: enablePose 
    });
  };

  // 停止分析
  const stopAnalysis = () => {
    // 停止幀擷取
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
    
    // 發送停止事件
    if (socketRef.current && socketRef.current.connected) {
      socketRef.current.emit('stop_analysis', {});
    }
    
    // 停止攝影機
    stopCamera();
    setIsAnalyzing(false);
  };

  // 更新比分
  const updateScore = (player: 1 | 2, delta: number) => {
    if (!matchState) return;
    
    const newState = { ...matchState };
    if (player === 1) {
      newState.player1_score = Math.max(0, newState.player1_score + delta);
    } else {
      newState.player2_score = Math.max(0, newState.player2_score + delta);
    }
    setMatchState(newState);
    
    // 發送更新
    if (socketRef.current && socketRef.current.connected) {
      socketRef.current.emit('update_score', {
        player1_score: newState.player1_score,
        player2_score: newState.player2_score
      });
    }
  };

  // 取得提醒樣式
  const getAlertStyle = (type: string) => {
    switch (type) {
      case 'critical':
        return 'bg-red-100 border-red-500 text-red-800';
      case 'warning':
        return 'bg-orange-100 border-orange-500 text-orange-800';
      case 'success':
        return 'bg-green-100 border-green-500 text-green-800';
      case 'tactic':
        return 'bg-blue-100 border-blue-500 text-blue-800';
      default:
        return 'bg-slate-100 border-slate-500 text-slate-800';
    }
  };

  // 清理
  useEffect(() => {
    return () => {
      stopCamera();
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
      }
      if (poseDetectionRef.current) {
        clearInterval(poseDetectionRef.current);
      }
    };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <Navbar />
      
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* 標題 */}
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-white flex items-center justify-center gap-3">
            <span className={`w-3 h-3 rounded-full ${isAnalyzing ? 'bg-red-500 animate-pulse' : 'bg-slate-500'}`}></span>
            🎬 即時比賽分析
          </h1>
          <p className="text-slate-400 mt-2">
            AI 教練即時觀看比賽，提供戰術建議和失誤提醒
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* 左側：視訊區域 */}
          <div className="lg:col-span-2 space-y-4">
            {/* 視訊畫面 */}
            <div className="bg-black rounded-2xl overflow-hidden shadow-2xl relative aspect-video">
              {/* 原始視訊 */}
              <video
                ref={videoRef}
                className="w-full h-full object-cover"
                playsInline
                muted
              />
              
              {/* 骨架覆蓋層 Canvas - 即時繪製骨架 */}
              {enablePose && (
                <canvas 
                  ref={overlayCanvasRef}
                  className="absolute top-0 left-0 w-full h-full pointer-events-none"
                />
              )}
              
              {/* 骨架載入狀態 */}
              {isAnalyzing && enablePose && !poseLoaded && (
                <div className="absolute bottom-4 left-4 bg-yellow-600 text-white px-3 py-1 rounded text-xs">
                  載入骨架模型中...
                </div>
              )}
              
              {/* 骨架偵測狀態 */}
              {isAnalyzing && enablePose && poseLoaded && (
                <div className="absolute bottom-4 left-4 bg-green-600 text-white px-3 py-1 rounded text-xs">
                  🦴 骨架偵測中
                </div>
              )}
              
              <canvas ref={canvasRef} className="hidden" />
              
              {/* 狀態覆蓋層 */}
              {!isAnalyzing && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/70">
                  <div className="text-center">
                    <div className="text-6xl mb-4">📹</div>
                    <p className="text-white text-lg">準備開始即時分析</p>
                    <p className="text-slate-400 text-sm mt-2">請確保攝影機對準比賽畫面</p>
                  </div>
                </div>
              )}
              
              {/* 即時狀態標籤 */}
              {isAnalyzing && (
                <>
                  <div className="absolute top-4 left-4 bg-red-600 text-white px-4 py-2 rounded-xl font-bold flex items-center gap-2">
                    <span className="w-2 h-2 bg-white rounded-full animate-pulse"></span>
                    LIVE 分析中
                  </div>
                  
                  {/* 骨架偵測狀態 */}
                  {enablePose && (
                    <div className="absolute top-16 left-4 bg-purple-600 text-white px-3 py-1 rounded-lg text-sm flex items-center gap-2">
                      🦴 骨架偵測中
                    </div>
                  )}
                  
                  {/* 比分顯示 */}
                  {matchState && (
                    <div className="absolute top-4 right-4 bg-black/80 text-white px-6 py-3 rounded-xl">
                      <div className="text-3xl font-bold font-mono text-center">
                        {matchState.player1_score} - {matchState.player2_score}
                      </div>
                    </div>
                  )}
                </>
              )}
              
              {cameraError && (
                <div className="absolute inset-0 flex items-center justify-center bg-red-900/80">
                  <div className="text-center text-white">
                    <div className="text-4xl mb-2">⚠️</div>
                    <p>{cameraError}</p>
                  </div>
                </div>
              )}
            </div>

            {/* 控制區域 */}
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6">
              <div className="flex flex-wrap items-center gap-4">
                {/* 選手輸入 */}
                <div className="flex-1 min-w-[200px]">
                  <input
                    type="text"
                    value={playerFocus}
                    onChange={(e) => setPlayerFocus(e.target.value)}
                    placeholder="關注選手名稱（可選）"
                    className="w-full px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    disabled={isAnalyzing}
                  />
                </div>
                
                {/* 骨架開關 */}
                <label className="flex items-center gap-2 text-white cursor-pointer">
                  <input
                    type="checkbox"
                    checked={enablePose}
                    onChange={(e) => setEnablePose(e.target.checked)}
                    disabled={isAnalyzing}
                    className="w-5 h-5 rounded accent-purple-500"
                  />
                  <span className="text-sm">🦴 骨架偵測</span>
                </label>
                
                {/* 開始/停止按鈕 */}
                {!isAnalyzing ? (
                  <button
                    onClick={startAnalysis}
                    className="px-8 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-bold rounded-xl hover:shadow-lg hover:scale-105 transition-all flex items-center gap-2"
                  >
                    <span>▶</span> 開始分析
                  </button>
                ) : (
                  <button
                    onClick={stopAnalysis}
                    className="px-8 py-3 bg-gradient-to-r from-red-500 to-rose-500 text-white font-bold rounded-xl hover:shadow-lg hover:scale-105 transition-all flex items-center gap-2"
                  >
                    <span>⏹</span> 停止分析
                  </button>
                )}
              </div>

              {/* 比分控制 */}
              {isAnalyzing && matchState && (
                <div className="mt-6 pt-6 border-t border-white/20">
                  <h3 className="text-white font-semibold mb-4">📊 比分記錄</h3>
                  <div className="grid grid-cols-2 gap-8">
                    {/* 選手 1 */}
                    <div className="text-center">
                      <div className="text-white/60 text-sm mb-2">選手 1</div>
                      <div className="flex items-center justify-center gap-3">
                        <button
                          onClick={() => updateScore(1, -1)}
                          className="w-10 h-10 bg-white/20 rounded-full text-white hover:bg-white/30 transition-colors"
                        >
                          -
                        </button>
                        <span className="text-4xl font-bold text-white font-mono w-16 text-center">
                          {matchState.player1_score}
                        </span>
                        <button
                          onClick={() => updateScore(1, 1)}
                          className="w-10 h-10 bg-green-500 rounded-full text-white hover:bg-green-600 transition-colors"
                        >
                          +
                        </button>
                      </div>
                    </div>
                    
                    {/* 選手 2 */}
                    <div className="text-center">
                      <div className="text-white/60 text-sm mb-2">選手 2</div>
                      <div className="flex items-center justify-center gap-3">
                        <button
                          onClick={() => updateScore(2, -1)}
                          className="w-10 h-10 bg-white/20 rounded-full text-white hover:bg-white/30 transition-colors"
                        >
                          -
                        </button>
                        <span className="text-4xl font-bold text-white font-mono w-16 text-center">
                          {matchState.player2_score}
                        </span>
                        <button
                          onClick={() => updateScore(2, 1)}
                          className="w-10 h-10 bg-green-500 rounded-full text-white hover:bg-green-600 transition-colors"
                        >
                          +
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 右側：提醒面板 */}
          <div className="lg:col-span-1">
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl overflow-hidden h-full flex flex-col">
              <div className="bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-4">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  🔔 即時提醒
                  <span className="bg-white/20 px-2 py-0.5 rounded-full text-sm">
                    {alerts.length}
                  </span>
                </h2>
              </div>
              
              <div className="flex-1 overflow-y-auto p-4 space-y-3 max-h-[600px]">
                {alerts.length === 0 ? (
                  <div className="text-center py-12 text-white/50">
                    <div className="text-4xl mb-3">🎯</div>
                    <p>等待分析結果...</p>
                    <p className="text-sm mt-1">AI 正在觀察比賽</p>
                  </div>
                ) : (
                  alerts.map((alert) => (
                    <div
                      key={alert.id}
                      className={`p-4 rounded-xl border-l-4 ${getAlertStyle(alert.alert_type)} animate-fadeIn`}
                    >
                      <div className="font-bold text-sm">{alert.title}</div>
                      <div className="text-sm mt-1">{alert.message}</div>
                      {alert.suggestion && (
                        <div className="text-xs mt-2 opacity-75 bg-white/50 rounded p-2">
                          💡 {alert.suggestion}
                        </div>
                      )}
                      <div className="text-xs opacity-50 mt-2">
                        {new Date(alert.timestamp * 1000).toLocaleTimeString()}
                      </div>
                    </div>
                  ))
                )}
                <div ref={alertsEndRef} />
              </div>

              {/* 弱點統計 */}
              {matchState && matchState.weakness_detected.length > 0 && (
                <div className="p-4 border-t border-white/20">
                  <h3 className="text-white/80 text-sm font-semibold mb-2">⚠️ 偵測到的弱點</h3>
                  <div className="flex flex-wrap gap-2">
                    {matchState.weakness_detected.map((w, i) => (
                      <span key={i} className="bg-red-500/30 text-red-200 px-2 py-1 rounded text-xs">
                        {w}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 錯誤提示 */}
        {error && (
          <div className="fixed bottom-4 right-4 bg-red-500 text-white px-6 py-3 rounded-xl shadow-lg">
            ❌ {error}
          </div>
        )}
      </main>

      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}
