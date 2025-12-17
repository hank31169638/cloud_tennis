'use client';

import { useState } from 'react';
import Navbar from '../components/Navbar';

export default function AnalyzePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string>('');
  const [videoPreview, setVideoPreview] = useState<string>('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('video/')) {
        setError('請選擇影片檔案');
        return;
      }
      if (file.size > 100 * 1024 * 1024) {
        setError('檔案不能超過 100MB');
        return;
      }
      setSelectedFile(file);
      setVideoPreview(URL.createObjectURL(file));
      setResult(null);
      setError('');
      setUploadProgress(0);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith('video/')) {
      if (file.size > 100 * 1024 * 1024) {
        setError('檔案不能超過 100MB');
        return;
      }
      setSelectedFile(file);
      setVideoPreview(URL.createObjectURL(file));
      setResult(null);
      setError('');
      setUploadProgress(0);
    } else {
      setError('請拖曳影片檔案');
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('請先選擇影片');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
      
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      const response = await fetch(`${apiUrl}/analyze`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || '分析失敗');
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || '分析時發生錯誤');
    } finally {
      setLoading(false);
      setTimeout(() => setUploadProgress(0), 1000);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setVideoPreview('');
    setResult(null);
    setError('');
    setUploadProgress(0);
  };

  const getClassColor = (className: string) => {
    switch (className?.toLowerCase()) {
      case 'good':
        return 'text-emerald-600';
      case 'normal':
        return 'text-amber-600';
      case 'bad':
        return 'text-rose-600';
      default:
        return 'text-gray-600';
    }
  };

  const getClassEmoji = (className: string) => {
    switch (className?.toLowerCase()) {
      case 'good':
        return '🎉';
      case 'normal':
        return '👍';
      case 'bad':
        return '⚠️';
      default:
        return '❓';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Upload Section */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              上傳影片
            </h2>
            {selectedFile && !loading && (
              <button
                onClick={handleReset}
                className="px-4 py-2 text-sm bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
              >
                重新選擇
              </button>
            )}
          </div>
          
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            className={`border-2 border-dashed rounded-2xl p-16 text-center transition-all cursor-pointer ${
              selectedFile 
                ? 'border-blue-400 bg-blue-50' 
                : 'border-blue-300 hover:border-blue-400 hover:bg-blue-50/30'
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
                <svg className="w-16 h-16 text-blue-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                {selectedFile ? (
                  <div>
                    <p className="text-base font-medium text-blue-900 mb-1">
                      {selectedFile.name}
                    </p>
                    <p className="text-sm text-blue-600">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-base font-medium text-blue-900 mb-1">
                      點擊選擇或拖曳影片
                    </p>
                    <p className="text-sm text-blue-600">
                      支援 MP4, AVI, MOV 格式，最大 100MB
                    </p>
                  </div>
                )}
              </div>
            </label>
          </div>

          {/* Upload Progress */}
          {uploadProgress > 0 && uploadProgress < 100 && (
            <div className="mt-6">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-blue-600">上傳進度</span>
                <span className="text-blue-900 font-medium">{uploadProgress}%</span>
              </div>
              <div className="bg-blue-100 rounded-full h-2.5 overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mt-6 px-4 py-3 bg-red-50 border border-red-200 rounded-xl">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={!selectedFile || loading}
            className="w-full mt-6 px-6 py-3.5 bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-full font-medium transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed hover:scale-[1.02] active:scale-[0.98] hover:from-blue-600 hover:to-indigo-600 shadow-md hover:shadow-lg"
          >
            {loading ? '分析中...' : '開始分析'}
          </button>
        </div>

        {/* Result Section */}
        {result && (
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-blue-200/50 p-8 shadow-sm">
            <h2 className="text-lg font-semibold text-blue-900 mb-6">
              分析結果
            </h2>

            {/* Main Result */}
            <div className="text-center py-8 mb-8 border-b border-blue-200">
              <div className="text-7xl mb-4">
                {getClassEmoji(result.classification)}
              </div>
              <div className={`text-3xl font-semibold mb-2 ${getClassColor(result.classification)}`}>
                {result.classification === 'good' ? '標準' : 
                 result.classification === 'normal' ? '一般' : 
                 result.classification === 'bad' ? '不標準' : '未知'}
              </div>
              <div className="text-sm text-blue-600 font-light">
                信心度: {(result.confidence * 100).toFixed(1)}%
              </div>
            </div>

            {/* Confidence Bar */}
            <div className="mb-8">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-blue-600">信心度</span>
                <span className="text-blue-900 font-medium">{(result.confidence * 100).toFixed(1)}%</span>
              </div>
              <div className="bg-blue-100 rounded-full h-3 overflow-hidden">
                <div 
                  className={`h-full rounded-full transition-all duration-500 ${
                    result.classification === 'good' ? 'bg-gradient-to-r from-emerald-500 to-teal-500' :
                    result.classification === 'normal' ? 'bg-gradient-to-r from-amber-500 to-yellow-500' :
                    'bg-gradient-to-r from-rose-500 to-red-500'
                  }`}
                  style={{ width: `${result.confidence * 100}%` }}
                />
              </div>
            </div>

            {/* Probabilities */}
            {result.probabilities && (
              <div>
                <h3 className="text-sm font-semibold text-blue-900 mb-4">
                  各類別機率
                </h3>
                <div className="space-y-3">
                  {Object.entries(result.probabilities)
                    .sort(([, a]: any, [, b]: any) => b - a)
                    .map(([className, probability]: any) => (
                      <div key={className} className="flex items-center gap-3">
                        <span className="w-16 text-sm text-blue-700 font-medium">
                          {className === 'good' ? '標準' : className === 'normal' ? '一般' : '不標準'}
                        </span>
                        <div className="flex-1 bg-blue-100 rounded-full h-2.5 overflow-hidden">
                          <div 
                            className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full rounded-full transition-all duration-500"
                            style={{ width: `${probability * 100}%` }}
                          />
                        </div>
                        <span className="w-12 text-right text-sm font-medium text-blue-900 tabular-nums">
                          {(probability * 100).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
