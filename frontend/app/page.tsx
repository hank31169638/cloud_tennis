'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Navbar from './components/Navbar';
import RankingTable from './components/RankingTable';
import StatsCard from './components/StatsCard';
import CategorySelector from './components/CategorySelector';

export default function Home() {
  const [selectedCategory, setSelectedCategory] = useState('SEN_SINGLES');
  const [rankingData, setRankingData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<string>('');

  const categoryNames: { [key: string]: string } = {
    'SEN_SINGLES': '男子單打',
    'SEN_DOUBLES': '男子雙打',
  };

  useEffect(() => {
    fetchRankingData(selectedCategory);
  }, [selectedCategory]);

  const fetchRankingData = async (category: string) => {
    setLoading(true)
    try {
      // 使用相對路徑 /api，Next.js 會自動代理到 localhost:5000
      const response = await fetch(`/api/rankings/${category}`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setRankingData(data);
      setLastUpdate(data.updated_at || new Date().toISOString());
    } catch (error) {
      console.error('獲取數據失敗:', error);
      setRankingData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleManualUpdate = async () => {
    setLoading(true)
    try {
      // 使用相對路徑 /api，Next.js 會自動代理到 localhost:5000
      await fetch(`/api/update`, { method: 'POST' })
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <Navbar />

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Header Section */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h2 className="text-3xl font-bold bg-gradient-to-r from-orange-600 via-pink-600 to-purple-600 bg-clip-text text-transparent">
              世界桌球排名
            </h2>
            <p className="mt-2 text-slate-600">實時更新的 ITTF 官方排名數據</p>
          </div>
          <button
            onClick={handleManualUpdate}
            disabled={loading}
            className="px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-cyan-700 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 shadow-lg"
          >
            {loading ? '🔄 更新中...' : '🔄 更新數據'}
          </button>
        </div>

        {/* Category Selector */}
        <div className="mb-6">
          <CategorySelector
            selectedCategory={selectedCategory}
            onCategoryChange={setSelectedCategory}
            categoryNames={categoryNames}
          />
        </div>

        {/* Stats Cards */}
        {!loading && rankingData && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <StatsCard
              title="總選手數"
              value={getTotalPlayers()}
              icon="👥"
              color="blue"
            />
            <StatsCard
              title="前二十名"
              value={getTopPlayers().length}
              icon="🏆"
              color="yellow"
            />
            <StatsCard
              title="參賽國家"
              value={getCountryDistribution().length}
              icon="🌍"
              color="green"
            />
          </div>
        )}

        {/* Country Distribution */}
        {!loading && rankingData && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">
              國家分布
            </h2>
            <div className="space-y-3">
              {getCountryDistribution().map(([country, count], index) => (
                <div key={country} className="flex items-center gap-3">
                  <span className="w-6 text-center text-sm font-medium text-gray-400">
                    {index + 1}
                  </span>
                  <span className="w-32 font-medium text-gray-900 text-sm">
                    {country}
                  </span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-gray-600 h-full rounded-full transition-all duration-500"
                      style={{ width: `${(count / getTotalPlayers()) * 100}%` }}
                    />
                  </div>
                  <span className="w-12 text-right text-sm font-medium text-gray-700">
                    {count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Ranking Table */}
        {loading ? (
          <div className="flex flex-col justify-center items-center h-64">
            <div className="w-12 h-12 border-3 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
            <p className="mt-4 text-sm text-gray-600">載入中...</p>
          </div>
        ) : rankingData ? (
          <div>
            <div className="mb-3 text-xs text-gray-500">
              更新時間: {new Date(lastUpdate).toLocaleString('zh-TW')}
            </div>
            <RankingTable data={getTopPlayers()} category={selectedCategory} />
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <p className="text-gray-400">暫無數據</p>
          </div>
        )}
      </main>
    </div>
  );
}
