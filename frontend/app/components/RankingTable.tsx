import Link from 'next/link';
import { useState } from 'react';

interface Player {
  CurrentRank: number;
  PlayerName?: string;
  CountryName?: string;
  RankingPointsYTD?: number;
  Points?: number;
  PreviousRank?: number;
  RankingDifference?: number;
  IttfId?: string;

  // Doubles fields
  PlayerName1?: string;
  IttfId1?: string;
  CountryName1?: string;
  PlayerName1d?: string;
  IttfId1d?: string;
  CountryName1d?: string;
}

interface RankingTableProps {
  data: Player[];
  category: string;
}

// SVG 預設頭像
const getDefaultAvatar = () => {
  return 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"%3E%3Ccircle cx="24" cy="24" r="24" fill="%23262626"/%3E%3Cpath d="M24 24c3.3 0 6-2.7 6-6s-2.7-6-6-6-6 2.7-6 6 2.7 6 6 6zm0 3c-4 0-12 2-12 6v3h24v-3c0-4-8-6-12-6z" fill="%23525252"/%3E%3C/svg%3E';
};

const PlayerAvatar = ({ ittfId, playerName, className }: { ittfId?: string, playerName?: string, className?: string }) => {
  const [hasSavedCache, setHasSavedCache] = useState(false);
  if (!ittfId || !playerName) return <img src={getDefaultAvatar()} alt="Default" className={className} />;

  // 生成頭像 URL - 方案 1: 空格轉 %20
  const getPlayerPhotoUrl = (id: string, name: string) => {
    const encodedName = name.replace(/ /g, '%20');
    return `https://photofiles.worldtabletennis.com/wtt-media/photos/400px/${id}_Headshot_R_${encodedName}.png`;
  };

  // 生成頭像 URL - 方案 2: 空格轉 _
  const getPlayerPhotoUrlWithUnderscore = (id: string, name: string) => {
    const encodedName = name.replace(/ /g, '_');
    return `https://photofiles.worldtabletennis.com/wtt-media/photos/400px/${id}_Headshot_R_${encodedName}.png`;
  };

  // 生成頭像 URL - 方案 3: HEADSHOT 大寫
  const getPlayerPhotoUrlUppercase = (id: string, name: string) => {
    const encodedName = name.replace(/ /g, '_');
    return `https://photofiles.worldtabletennis.com/wtt-media/photos/400px/${id}_HEADSHOT_R_${encodedName}.png`;
  };

  // 生成頭像 URL - 方案 4: 名字前後對調
  const getPlayerPhotoUrlReversed = (id: string, name: string) => {
    const parts = name.split(' ');
    if (parts.length >= 2) {
      const reversedName = `${parts[1]}_${parts[0]}`;
      return `https://photofiles.worldtabletennis.com/wtt-media/photos/400px/${id}_Headshot_R_${reversedName}.png`;
    }
    return getPlayerPhotoUrl(id, name);
  };

  // 生成頭像 URL - 方案 5: 連字符轉底線
  const getPlayerPhotoUrlHyphenToUnderscore = (id: string, name: string) => {
    const encodedName = name.replace(/ /g, '_').replace(/-/g, '_');
    return `https://photofiles.worldtabletennis.com/wtt-media/photos/400px/${id}_Headshot_R_${encodedName}.png`;
  };

  // 生成頭像 URL - 方案 6: 混合編碼
  const getPlayerPhotoUrlMixedEncoding = (id: string, name: string) => {
    const parts = name.split(' ');
    if (parts.length >= 2) {
      const firstName = parts[0];
      const restName = parts.slice(1).join('%20');
      const encodedName = `${firstName}_${restName}`;
      return `https://photofiles.worldtabletennis.com/wtt-media/photos/400px/${id}_Headshot_R_${encodedName}.png`;
    }
    return getPlayerPhotoUrl(id, name);
  };

  // 生成頭像 URL - 方案 7: 全小寫
  const getPlayerPhotoUrlLowercase = (id: string, name: string) => {
    const encodedName = name.toLowerCase().replace(/ /g, '_').replace(/-/g, '_');
    return `https://photofiles.worldtabletennis.com/wtt-media/photos/400px/${id}_Headshot_R_${encodedName}.png`;
  };

  return (
    <img
      src={getPlayerPhotoUrl(ittfId, playerName)}
      alt={playerName}
      className={className}
      onLoad={(e) => {
        const currentSrc = e.currentTarget.src;
        if (currentSrc && !hasSavedCache && !currentSrc.includes('data:image/svg+xml')) {
          setHasSavedCache(true);
          fetch('/api/players/photo/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              ittf_id: ittfId,
              name: playerName,
              photo_url: currentSrc
            })
          }).catch(console.error);
        }
      }}
      onError={(e) => {
        const target = e.currentTarget;
        const retry = target.dataset.retry || '0';

        if (retry === '0') {
          target.dataset.retry = '1';
          target.src = getPlayerPhotoUrlWithUnderscore(ittfId, playerName);
        } else if (retry === '1') {
          target.dataset.retry = '2';
          target.src = getPlayerPhotoUrlUppercase(ittfId, playerName);
        } else if (retry === '2') {
          target.dataset.retry = '3';
          target.src = getPlayerPhotoUrlReversed(ittfId, playerName);
        } else if (retry === '3') {
          target.dataset.retry = '4';
          target.src = getPlayerPhotoUrlHyphenToUnderscore(ittfId, playerName);
        } else if (retry === '4') {
          target.dataset.retry = '5';
          target.src = getPlayerPhotoUrlMixedEncoding(ittfId, playerName);
        } else if (retry === '5') {
          target.dataset.retry = '6';
          target.src = getPlayerPhotoUrlLowercase(ittfId, playerName);
        } else {
          target.dataset.retry = '7';
          target.src = getDefaultAvatar();
        }
      }}
    />
  );
};

export default function RankingTable({ data, category }: RankingTableProps) {
  const isDoubles = category.includes('DOUBLES');

  // 安全檢查：確保 data 是陣列
  if (!data || !Array.isArray(data)) {
    return (
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-12 text-center">
        <p className="text-neutral-500">暫無數據</p>
      </div>
    );
  }





  const getRankChange = (current: number, previous?: number) => {
    if (!previous || previous === current) return null;
    const change = previous - current;
    if (change > 0) {
      return <span className="text-emerald-500 text-xs font-medium">↑ {change}</span>;
    } else if (change < 0) {
      return <span className="text-red-500 text-xs font-medium">↓ {Math.abs(change)}</span>;
    }
    return null;
  };

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full">
          <thead className="border-b border-neutral-800 bg-neutral-800/50">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">
                排名
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">
                {isDoubles ? '選手組合' : '選手'}
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">
                國家
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">
                積分
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">
                變化
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-800">
            {data.map((player, index) => (
              <tr
                key={index}
                className="hover:bg-neutral-800/50 transition-colors"
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    {player.CurrentRank <= 3 ? (
                      <span className="w-7 h-7 flex items-center justify-center text-sm font-semibold rounded-full bg-white text-neutral-900">
                        {player.CurrentRank}
                      </span>
                    ) : (
                      <span className="w-7 h-7 flex items-center justify-center text-sm font-medium text-neutral-400">
                        {player.CurrentRank}
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-3">
                    {isDoubles ? (
                      <div className="flex flex-col gap-2">
                        <Link href={`/player-analysis?player=${encodeURIComponent(player.PlayerName1 || '')}`} className="flex items-center gap-2 group">
                          <PlayerAvatar
                            ittfId={player.IttfId1}
                            playerName={player.PlayerName1}
                            className="w-8 h-8 rounded-full object-cover border border-neutral-700 group-hover:border-neutral-500 transition-colors"
                          />
                          <span className="text-sm font-medium text-neutral-200 group-hover:text-white transition-colors">
                            {player.PlayerName1}
                          </span>
                        </Link>
                        <Link href={`/player-analysis?player=${encodeURIComponent(player.PlayerName1d || '')}`} className="flex items-center gap-2 group">
                          <PlayerAvatar
                            ittfId={player.IttfId1d}
                            playerName={player.PlayerName1d}
                            className="w-8 h-8 rounded-full object-cover border border-neutral-700 group-hover:border-neutral-500 transition-colors"
                          />
                          <span className="text-sm font-medium text-neutral-200 group-hover:text-white transition-colors">
                            {player.PlayerName1d}
                          </span>
                        </Link>
                      </div>
                    ) : (
                      <Link href={`/player-analysis?player=${encodeURIComponent(player.PlayerName || '')}`} className="flex items-center gap-3 group">
                        <PlayerAvatar
                          ittfId={player.IttfId}
                          playerName={player.PlayerName}
                          className="w-10 h-10 rounded-full object-cover border border-neutral-700 group-hover:border-neutral-500 transition-colors"
                        />
                        <span className="text-sm font-medium text-neutral-200 group-hover:text-white transition-colors">
                          {player.PlayerName}
                        </span>
                      </Link>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {isDoubles ? (
                    <div className="flex flex-col gap-2">
                      <span className="text-xs font-medium text-neutral-400 bg-neutral-800 px-3 py-1 rounded-full w-fit">
                        {player.CountryName1}
                      </span>
                      <span className="text-xs font-medium text-neutral-400 bg-neutral-800 px-3 py-1 rounded-full w-fit">
                        {player.CountryName1d}
                      </span>
                    </div>
                  ) : (
                    <span className="text-xs font-medium text-neutral-400 bg-neutral-800 px-3 py-1 rounded-full">
                      {player.CountryName}
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-sm font-semibold text-white tabular-nums">
                    {(player.RankingPointsYTD || player.Points)?.toLocaleString()}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getRankChange(player.CurrentRank, player.PreviousRank)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
