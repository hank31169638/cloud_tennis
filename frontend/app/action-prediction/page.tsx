"use client";

import { useState } from "react";
import Navbar from "../components/Navbar";

interface PredictionResult {
  prediction: string;
  confidence: number;
  probabilities: {
    不標準: number;
    標準: number;
  };
  filename: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:5000";

export default function ActionPredictionPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [error, setError] = useState<string>("");
  const [videoPreview, setVideoPreview] = useState<string>("");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith("video/")) {
        setError("請選擇影片檔案");
        return;
      }
      if (file.size > 100 * 1024 * 1024) {
        setError("檔案不能超過 100MB");
        return;
      }
      setSelectedFile(file);
      setVideoPreview(URL.createObjectURL(file));
      setResult(null);
      setError("");
      setUploadProgress(0);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("video/")) {
      if (file.size > 100 * 1024 * 1024) {
        setError("檔案不能超過 100MB");
        return;
      }
      setSelectedFile(file);
      setVideoPreview(URL.createObjectURL(file));
      setResult(null);
      setError("");
      setUploadProgress(0);
    } else {
      setError("請拖曳影片檔案");
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError("請先選擇影片");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      // 模擬上傳進度
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      const response = await fetch(`${API_URL}/api/action-prediction`, {
        method: "POST",
        body: formData,
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "分析失敗");
      }

      const data = await response.json();

      if (data.success) {
        setResult(data);
      } else {
        throw new Error(data.error || "分析失敗");
      }
    } catch (err: any) {
      setError(err.message || "分析時發生錯誤");
    } finally {
      setLoading(false);
      setTimeout(() => setUploadProgress(0), 1000);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    if (videoPreview) {
      URL.revokeObjectURL(videoPreview);
    }
    setVideoPreview("");
    setResult(null);
    setError("");
    setUploadProgress(0);
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      <main className="container mx-auto px-4 py-8 max-w-5xl">
        {/* 標題 */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            🏓 動作標準分析
          </h1>
          <p className="text-gray-600">
            使用 AI 模型分析桌球動作是否標準
          </p>
        </div>

        {/* 上傳區域 */}
        <div className="bg-white rounded-xl p-6 mb-6 border border-gray-200 shadow-sm">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900">上傳影片</h2>
            {selectedFile && !loading && (
              <button
                onClick={handleReset}
                className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                重新選擇
              </button>
            )}
          </div>

          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer ${selectedFile
                ? "border-blue-400 bg-blue-50"
                : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
              }`}
          >
            <input
              type="file"
              accept="video/*"
              onChange={handleFileChange}
              className="hidden"
              id="fileInput"
              disabled={loading}
            />
            <label htmlFor="fileInput" className="cursor-pointer">
              <div className="flex flex-col items-center">
                <svg
                  className="w-16 h-16 text-blue-500 mb-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                  />
                </svg>
                {selectedFile ? (
                  <div>
                    <p className="text-base font-medium text-gray-900 mb-1">
                      {selectedFile.name}
                    </p>
                    <p className="text-sm text-gray-600">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-base font-medium text-gray-900 mb-1">
                      點擊選擇或拖曳影片
                    </p>
                    <p className="text-sm text-gray-600">
                      支援 MP4, AVI, MOV 格式，最大 100MB
                    </p>
                  </div>
                )}
              </div>
            </label>
          </div>

          {/* 影片預覽 */}
          {videoPreview && (
            <div className="mt-6">
              <video
                src={videoPreview}
                controls
                className="w-full rounded-lg max-h-96 bg-black"
              />
            </div>
          )}

          {/* 上傳進度 */}
          {uploadProgress > 0 && uploadProgress < 100 && (
            <div className="mt-6">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-blue-600">處理進度</span>
                <span className="text-gray-900 font-medium">{uploadProgress}%</span>
              </div>
              <div className="bg-gray-200 rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* 錯誤訊息 */}
          {error && (
            <div className="mt-6 px-4 py-3 bg-red-50 border border-red-200 rounded-xl">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* 上傳按鈕 */}
          <button
            onClick={handleUpload}
            disabled={!selectedFile || loading}
            className={`w-full mt-6 px-6 py-3.5 rounded-lg font-medium transition-all duration-200 ${!selectedFile || loading
                ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                : "bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-500 hover:to-indigo-500 shadow-lg hover:shadow-xl"
              }`}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg
                  className="animate-spin h-5 w-5"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                分析中...
              </span>
            ) : (
              "🔍 開始分析"
            )}
          </button>
        </div>

        {/* 分析結果 */}
        {result && (
          <div className="bg-white rounded-xl p-8 border border-gray-200 shadow-lg">
            <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">
              分析結果
            </h2>

            {/* 主要結果 */}
            <div className="text-center py-8 mb-8 border-b border-gray-200">
              <div className="text-7xl mb-4">
                {result.prediction === "標準" ? "✅" : "❌"}
              </div>
              <div
                className={`text-4xl font-bold mb-2 ${result.prediction === "標準"
                    ? "text-green-600"
                    : "text-red-600"
                  }`}
              >
                {result.prediction}
              </div>
              <div className="text-sm text-gray-600 font-light">
                信心度: {(result.confidence * 100).toFixed(1)}%
              </div>
            </div>

            {/* 信心度進度條 */}
            <div className="mb-8">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-600">信心度</span>
                <span className="text-gray-900 font-medium">
                  {(result.confidence * 100).toFixed(1)}%
                </span>
              </div>
              <div className="bg-gray-200 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${result.prediction === "標準"
                      ? "bg-gradient-to-r from-green-500 to-emerald-500"
                      : "bg-gradient-to-r from-red-500 to-rose-500"
                    }`}
                  style={{ width: `${result.confidence * 100}%` }}
                />
              </div>
            </div>

            {/* 機率分佈 */}
            {result.probabilities && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  各類別機率
                </h3>
                <div className="space-y-4">
                  {Object.entries(result.probabilities)
                    .sort(([, a], [, b]) => b - a)
                    .map(([className, probability]) => (
                      <div key={className} className="flex items-center gap-4">
                        <span className="w-20 text-sm text-gray-700 font-medium">
                          {className}
                        </span>
                        <div className="flex-1 bg-gray-200 rounded-full h-3 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${className === "標準"
                                ? "bg-gradient-to-r from-green-500 to-emerald-500"
                                : "bg-gradient-to-r from-red-500 to-rose-500"
                              }`}
                            style={{ width: `${probability * 100}%` }}
                          />
                        </div>
                        <span className="w-16 text-right text-sm font-medium text-gray-900 tabular-nums">
                          {(probability * 100).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* 建議 */}
            <div className="mt-8 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
              <h4 className="text-sm font-semibold text-yellow-700 mb-2">
                💡 建議
              </h4>
              <p className="text-sm text-gray-700">
                {result.prediction === "標準"
                  ? "您的動作看起來很標準！繼續保持這個姿勢和技術。"
                  : "建議您參考專業教練的指導，調整動作姿勢以提高技術水平。"}
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

