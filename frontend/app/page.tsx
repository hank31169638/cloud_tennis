'use client';

import { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import RankingTable from './components/RankingTable';

export default function Home() {
  const [selectedCategory, setSelectedCategory] = useState('SEN_SINGLES');
  const [rankingData, setRankingData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const [error, setError] = useState<string>('');

  const categories = [
    { key: 'SEN_SINGLES', label: '男子單打' },
    { key: 'SEN_DOUBLES', label: '男子雙打' },
  ];

  useEffect(() => {
    fetchRankingData(selectedCategory);
  }, [selectedCategory]);

  const fetchRankingData = async (category: string) => {
    setLoading(true);
    setError('');
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
      const response = await fetch(`${apiUrl}/api/rankings/${category}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setRankingData(data);
      setLastUpdate(data.updated_at || new Date().toISOString());
      setError('');
    } catch (error: any) {
      console.error('獲取數據失敗:', error);
      setRankingData(null);
      
      // 提供更友好的錯誤訊息
      if (error.message?.includes('Failed to fetch') || error.name === 'TypeError') {
        setError(`無法連接到後端服務器。請確認：
          1. 後端服務器是否正在運行 (${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'})
          2. 檢查網絡連接
          3. 檢查 CORS 配置`);
      } else {
        setError(error.message || '獲取數據失敗，請稍後再試');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleManualUpdate = async () => {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
      await fetch(`${apiUrl}/api/update`, { method: 'POST' });
      fetchRankingData(selectedCategory);
    } catch (error) {
      console.error('更新數據失敗:', error);
      setLoading(false);
    }
  };

  const getRankingList = () => {
    if (!rankingData?.data?.Result) return [];
    return rankingData.data.Result;
  };

  const getTopPlayers = () => {
    const list = getRankingList();
    return list.slice(0, 20);
  };

  const getTotalPlayers = () => {
    return getRankingList().length;
  };

  const getCountryDistribution = () => {
    const list = getRankingList();
    if (!list || list.length === 0) return [];
    
    const countries: { [key: string]: number } = {};
    list.forEach((player: any) => {
      const country = player.CountryName || '未知';
      countries[country] = (countries[country] || 0) + 1;
    });
    
    return Object.entries(countries)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
  };

  return (
    <div className="min-h-screen bg-neutral-950">
      <Navbar />

      <main className="max-w-6xl mx-auto px-6 py-10">
        {/* Header Section */}
        <div className="mb-10">
          <h2 className="text-3xl font-semibold text-white tracking-tight">
            世界桌球排名
          </h2>
          <p className="mt-2 text-neutral-500">ITTF 官方排名數據</p>
        </div>

        {/* Stats + Controls Row */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
          {/* Category Tabs */}
          <div className="flex gap-2">
            {categories.map((cat) => (
              <button
                key={cat.key}
                onClick={() => setSelectedCategory(cat.key)}
                className={`px-4 py-2 text-sm font-medium rounded-full transition-all duration-200
                  ${selectedCategory === cat.key
                    ? 'bg-white text-neutral-900'
                    : 'bg-neutral-800 text-neutral-400 hover:text-white hover:bg-neutral-700'
                  }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Update Button */}
          <button
            onClick={handleManualUpdate}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium rounded-full bg-neutral-800 text-neutral-300 
                       hover:bg-neutral-700 hover:text-white transition-all duration-200
                       disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {loading ? '更新中...' : '更新數據'}
          </button>
        </div>

        {/* Stats Cards */}
        {!loading && rankingData && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5">
              <div className="text-neutral-500 text-sm mb-1">總選手數</div>
              <div className="text-2xl font-semibold text-white">{getTotalPlayers()}</div>
            </div>
            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5">
              <div className="text-neutral-500 text-sm mb-1">前二十名</div>
              <div className="text-2xl font-semibold text-white">{getTopPlayers().length}</div>
            </div>
            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5">
              <div className="text-neutral-500 text-sm mb-1">參賽國家</div>
              <div className="text-2xl font-semibold text-white">{getCountryDistribution().length}+</div>
            </div>
          </div>
        )}

        {/* Country Distribution */}
        {!loading && rankingData && (
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 mb-8">
            <h3 className="text-sm font-medium text-neutral-400 uppercase tracking-wider mb-4">
              國家分布
            </h3>
            <div className="space-y-3">
              {getCountryDistribution().map(([country, count], index) => (
                <div key={country} className="flex items-center gap-3">
                  <span className="w-6 text-center text-sm font-medium text-neutral-500">
                    {index + 1}
                  </span>
                  <span className="w-28 text-sm text-neutral-300">
                    {country}
                  </span>
                  <div className="flex-1 bg-neutral-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-white h-full rounded-full transition-all duration-500"
                      style={{ width: `${Math.max((count / getTotalPlayers()) * 100 * 5, 5)}%` }}
                    />
                  </div>
                  <span className="w-10 text-right text-sm font-medium text-neutral-400">
                    {count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="bg-red-900/20 border border-red-800 rounded-xl p-6 mb-8">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <h3 className="text-red-400 font-semibold mb-2">連接錯誤</h3>
                <p className="text-red-300 text-sm whitespace-pre-line">{error}</p>
                <button
                  onClick={() => fetchRankingData(selectedCategory)}
                  className="mt-4 px-4 py-2 text-sm bg-red-900/50 text-red-300 rounded-lg hover:bg-red-900/70 transition-colors"
                >
                  重試
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Ranking Table */}
        {loading ? (
          <div className="flex flex-col justify-center items-center h-64">
            <div className="w-10 h-10 border-2 border-neutral-700 border-t-white rounded-full animate-spin"></div>
            <p className="mt-4 text-sm text-neutral-500">載入中...</p>
          </div>
        ) : rankingData ? (
          <div>
            <div className="mb-4 text-xs text-neutral-500 flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              更新時間: {new Date(lastUpdate).toLocaleString('zh-TW')}
            </div>
            <RankingTable data={getTopPlayers()} category={selectedCategory} />
          </div>
        ) : !error ? (
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-12 text-center">
            <p className="text-neutral-500">暫無數據</p>
          </div>
        ) : null}
      </main>
    </div>
  );
}
