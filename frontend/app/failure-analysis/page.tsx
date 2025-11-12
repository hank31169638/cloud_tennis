'use client'

import { useState } from 'react'
import Navbar from '../components/Navbar'

interface AnalysisResult {
  success: boolean
  analysis?: {
    ai_analysis: {
      failure_reason: string
      category: string
      detailed_analysis: {
        stance?: string
        racket_angle?: string
        body_balance?: string
        timing?: string
      }
      improvement_suggestions: string[]
      summary: string
      severity: 'minor' | 'moderate' | 'severe'
    }
    structured_data: {
      video_info: {
        duration_seconds: number
      }
      pose_analysis: {
        analyzed_frames: number
        avg_racket_angle: number
        racket_angle_variance: number
      }
      technical_indicators: {
        stance: string
        racket_control: string
        body_balance: string
      }
    }
  }
  error?: string
}

const severityColors = {
  minor: 'bg-green-50 text-green-700 border-green-200',
  moderate: 'bg-amber-50 text-amber-700 border-amber-200',
  severe: 'bg-red-50 text-red-700 border-red-200'
}

const severityText = {
  minor: '輕微',
  moderate: '中等',
  severe: '嚴重'
}

export default function FailureAnalysisPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [videoPreview, setVideoPreview] = useState<string | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [useGemini, setUseGemini] = useState(true)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.type.startsWith('video/')) {
      setSelectedFile(file)
      setVideoPreview(URL.createObjectURL(file))
      setResult(null)
    }
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('video/')) {
      setSelectedFile(file)
      setVideoPreview(URL.createObjectURL(file))
      setResult(null)
    }
  }

  const handleAnalyze = async () => {
    if (!selectedFile) return

    setIsAnalyzing(true)
    setResult(null)

    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('use_gemini', useGemini.toString())

    try {
      // 使用環境變數
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
      
      const response = await fetch(`${apiUrl}/api/analyze-failure`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setResult(data)
    } catch (error) {
      setResult({
        success: false,
        error: `網路錯誤: ${error}`
      })
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            🤖 AI 失誤分析
          </h1>
          <p className="text-gray-600">
            上傳您的失分影片，獲得 AI 專業分析與改進建議
          </p>
        </div>

        {/* Upload Section */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">上傳失誤影片</h2>
          
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center bg-gray-50 hover:bg-gray-100 transition-colors cursor-pointer"
          >
            <input
              type="file"
              accept="video/*"
              onChange={handleFileSelect}
              className="hidden"
              id="video-upload"
            />
            <label htmlFor="video-upload" className="cursor-pointer">
              <div className="text-5xl mb-3">📤</div>
              <p className="text-base text-gray-900 font-medium mb-1">
                點擊或拖曳影片檔案到這裡
              </p>
              <p className="text-sm text-gray-500">支援格式: MP4, AVI, MOV, MKV</p>
              <p className="text-sm text-gray-500">建議時長: 3-5 秒</p>
            </label>
          </div>

          {/* Options */}
          <div className="mt-4 flex items-center gap-2">
            <input
              type="checkbox"
              id="use-gemini"
              checked={useGemini}
              onChange={(e) => setUseGemini(e.target.checked)}
              className="w-4 h-4 text-purple-600 rounded"
            />
            <label htmlFor="use-gemini" className="text-gray-900 font-medium text-sm">
              使用 Gemini AI 深度分析 🤖
            </label>
          </div>

          {/* Video Preview */}
          {videoPreview && (
            <div className="mt-6">
              <video
                src={videoPreview}
                controls
                className="w-full max-w-2xl mx-auto rounded-lg border border-gray-200"
              />
              <p className="text-center mt-2 text-sm text-gray-600">
                已選擇: {selectedFile?.name}
              </p>
            </div>
          )}

          {/* Analyze Button */}
          <button
            onClick={handleAnalyze}
            disabled={!selectedFile || isAnalyzing}
            className="mt-6 w-full bg-purple-600 hover:bg-purple-700 text-white font-medium py-3 px-6 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isAnalyzing ? (
              <span className="flex items-center justify-center gap-2">
                <span className="inline-block animate-spin">⚙️</span>
                正在分析中...
              </span>
            ) : (
              '開始分析'
            )}
          </button>
        </div>

        {/* Results Section */}
        {isAnalyzing && (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <div className="text-5xl mb-3 inline-block animate-spin">⚙️</div>
            <p className="text-base text-gray-900 font-medium">正在分析影片，請稍候...</p>
          </div>
        )}

        {result && result.success && result.analysis && (
          <div className="space-y-6">
            {/* Main Failure Reason */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-start justify-between mb-3">
                <h2 className="text-lg font-bold text-gray-900">🎯 失誤原因</h2>
                <span className={`px-3 py-1 rounded-lg text-xs font-medium border ${severityColors[result.analysis.ai_analysis.severity]}`}>
                  {severityText[result.analysis.ai_analysis.severity]}
                </span>
              </div>
              <p className="text-base text-gray-700 leading-relaxed">
                {result.analysis.ai_analysis.failure_reason}
              </p>
            </div>

            {/* Category */}
            <div className="bg-gray-50 rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-2">📋 問題類別</h2>
              <p className="text-base text-gray-700">{result.analysis.ai_analysis.category}</p>
            </div>

            {/* Detailed Analysis */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">🔍 詳細分析</h2>
              <div className="space-y-3">
                {result.analysis.ai_analysis.detailed_analysis && 
                  Object.entries(result.analysis.ai_analysis.detailed_analysis).map(([key, value]) => (
                  <div key={key} className="bg-gray-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-gray-900 mb-1 text-sm">
                      {key === 'stance' && '站位'}
                      {key === 'racket_angle' && '拍面角度'}
                      {key === 'body_balance' && '身體平衡'}
                      {key === 'timing' && '擊球時機'}
                    </h3>
                    <p className="text-sm text-gray-700">{value}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Improvement Suggestions */}
            <div className="bg-blue-50 rounded-lg border border-blue-200 p-6">
              <h2 className="text-lg font-bold text-blue-900 mb-4 flex items-center gap-2">
                <span className="text-xl">💡</span>
                改進建議
              </h2>
              <ul className="space-y-2">
                {result.analysis.ai_analysis.improvement_suggestions && 
                  Array.isArray(result.analysis.ai_analysis.improvement_suggestions) &&
                  result.analysis.ai_analysis.improvement_suggestions.map((suggestion, index) => (
                  <li key={index} className="flex items-start gap-2 bg-white p-3 rounded-lg border-l-4 border-blue-500">
                    <span className="text-blue-600 flex-shrink-0">✓</span>
                    <span className="text-sm text-gray-700">{suggestion}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Summary */}
            <div className="bg-purple-600 rounded-lg p-6 text-white">
              <h2 className="text-lg font-bold mb-2">📝 總結</h2>
              <p className="text-sm">{result.analysis.ai_analysis.summary}</p>
            </div>

            {/* Technical Data */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                <span className="text-xl">📊</span>
                技術數據
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-gray-600 text-xs mb-1">影片時長</div>
                  <div className="text-lg font-bold text-gray-900">
                    {result.analysis.structured_data.video_info.duration_seconds.toFixed(2)} 秒
                  </div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-gray-600 text-xs mb-1">分析幀數</div>
                  <div className="text-lg font-bold text-gray-900">
                    {result.analysis.structured_data.pose_analysis.analyzed_frames} 幀
                  </div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-gray-600 text-xs mb-1">平均拍面角度</div>
                  <div className="text-lg font-bold text-gray-900">
                    {result.analysis.structured_data.pose_analysis.avg_racket_angle.toFixed(1)}°
                  </div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-gray-600 text-xs mb-1">站位評估</div>
                  <div className="text-lg font-bold text-gray-900">
                    {result.analysis.structured_data.technical_indicators.stance}
                  </div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-gray-600 text-xs mb-1">拍面控制</div>
                  <div className="text-lg font-bold text-gray-900">
                    {result.analysis.structured_data.technical_indicators.racket_control}
                  </div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-gray-600 text-xs mb-1">身體平衡</div>
                  <div className="text-lg font-bold text-gray-900">
                    {result.analysis.structured_data.technical_indicators.body_balance}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {result && !result.success && (
          <div className="bg-red-50 border border-red-300 rounded-lg p-6">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl text-red-600">⚠️</span>
              <h2 className="text-lg font-bold text-red-900">分析失敗</h2>
            </div>
            <p className="text-sm text-red-800">{result.error}</p>
          </div>
        )}
      </div>
    </div>
  )
}
