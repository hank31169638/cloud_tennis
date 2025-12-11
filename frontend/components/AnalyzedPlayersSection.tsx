'use client';

import React, { useState, useEffect } from 'react';

interface PlayerSummary {
    player_id: string;
    display_name: string;
    total_matches: number;
    last_updated: string;
    aggregate_ratings?: {
        serve?: number;
        receive?: number;
        attack?: number;
        defense?: number;
        tactics?: number;
    };
}

interface AnalyzedPlayersSectionProps {
    onPlayerClick: (playerName: string) => void;
}

export default function AnalyzedPlayersSection({ onPlayerClick }: AnalyzedPlayersSectionProps) {
    const [players, setPlayers] = useState<PlayerSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchPlayers();
    }, []);

    const fetchPlayers = async () => {
        try {
            setLoading(true);
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:5000';
            const response = await fetch(`${apiUrl}/api/players/profiles`);
            const data = await response.json();

            if (data.success) {
                setPlayers(data.profiles || []);
            } else {
                setError(data.error || '無法載入選手資料');
            }
        } catch (err) {
            setError('連線錯誤');
        } finally {
            setLoading(false);
        }
    };

    const getAverageRating = (ratings?: PlayerSummary['aggregate_ratings']) => {
        if (!ratings) return 0;
        const values = Object.values(ratings).filter(v => v !== undefined) as number[];
        if (values.length === 0) return 0;
        return values.reduce((a, b) => a + b, 0) / values.length;
    };

    const getRatingColor = (rating: number) => {
        if (rating >= 8) return 'from-green-500 to-emerald-500';
        if (rating >= 6) return 'from-blue-500 to-cyan-500';
        if (rating >= 4) return 'from-yellow-500 to-orange-500';
        return 'from-red-500 to-pink-500';
    };

    if (loading) {
        return (
            <div className="bg-white border border-neutral-200 rounded-2xl p-8">
                <div className="flex items-center justify-center gap-3">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-neutral-900"></div>
                    <span className="text-neutral-500">載入選手資料...</span>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-white border border-neutral-200 rounded-2xl p-8">
                <p className="text-center text-neutral-500">{error}</p>
            </div>
        );
    }

    if (players.length === 0) {
        return (
            <div className="bg-white border border-neutral-200 rounded-2xl p-8">
                <div className="text-center">
                    <div className="text-4xl mb-3">🏓</div>
                    <h3 className="font-medium text-neutral-700 mb-2">尚無分析紀錄</h3>
                    <p className="text-sm text-neutral-400">分析 YouTube 比賽影片後，選手資料會自動儲存於此</p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white border border-neutral-200 rounded-2xl overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 border-b border-neutral-100 flex items-center justify-between">
                <h2 className="text-lg font-bold text-neutral-900 flex items-center gap-2">
                    <span className="text-xl">📊</span> 已分析選手
                </h2>
                <span className="text-sm text-neutral-400">{players.length} 位選手</span>
            </div>

            {/* Player Grid */}
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {players.map((player) => {
                    const avgRating = getAverageRating(player.aggregate_ratings);
                    return (
                        <div
                            key={player.player_id}
                            onClick={() => onPlayerClick(player.display_name)}
                            className="group relative bg-gradient-to-br from-neutral-50 to-white border border-neutral-200 rounded-xl p-4 hover:shadow-lg hover:border-blue-200 cursor-pointer transition-all duration-200"
                        >
                            {/* Rating Badge */}
                            <div className={`absolute top-3 right-3 px-2 py-1 rounded-full text-xs font-bold text-white bg-gradient-to-r ${getRatingColor(avgRating)}`}>
                                {avgRating > 0 ? avgRating.toFixed(1) : '-'}
                            </div>

                            {/* Player Info */}
                            <div className="flex items-center gap-3 mb-3">
                                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">
                                    {player.display_name.charAt(0)}
                                </div>
                                <div>
                                    <h3 className="font-bold text-neutral-900 group-hover:text-blue-600 transition-colors">
                                        {player.display_name}
                                    </h3>
                                    <p className="text-xs text-neutral-400">
                                        {player.total_matches} 場比賽
                                    </p>
                                </div>
                            </div>

                            {/* Mini Ratings */}
                            {player.aggregate_ratings && Object.keys(player.aggregate_ratings).length > 0 && (
                                <div className="space-y-1.5">
                                    {[
                                        { label: '發球', key: 'serve' },
                                        { label: '進攻', key: 'attack' },
                                        { label: '戰術', key: 'tactics' }
                                    ].map(({ label, key }) => {
                                        const value = player.aggregate_ratings?.[key as keyof typeof player.aggregate_ratings] || 0;
                                        return (
                                            <div key={key} className="flex items-center gap-2">
                                                <span className="text-xs text-neutral-500 w-8">{label}</span>
                                                <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded-full"
                                                        style={{ width: `${value * 10}%` }}
                                                    ></div>
                                                </div>
                                                <span className="text-xs font-medium text-neutral-600 w-6 text-right">
                                                    {value > 0 ? value.toFixed(1) : '-'}
                                                </span>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}

                            {/* Last Updated */}
                            <div className="mt-3 pt-3 border-t border-neutral-100 text-xs text-neutral-400">
                                最後更新: {new Date(player.last_updated).toLocaleDateString('zh-TW')}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
