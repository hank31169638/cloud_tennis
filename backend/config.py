"""
配置管理模組
統一管理所有環境變數和應用程式配置
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv

# 載入 .env 檔案
# 載入 .env 檔案 (強制覆寫系統環境變數，避免舊 Key 殘留)
load_dotenv(override=True)

# Debug: 檢查 API Key (印出前 10 碼)
_api_key = os.getenv('GEMINI_API_KEY')
if _api_key:
    print(f"[KEY] Current Loaded API Key: {_api_key[:10]}...")
else:
    print("[WARNING] No API Key found in environment!")


@dataclass
class AppConfig:
    """應用程式基本配置"""
    APP_NAME: str = "Table Tennis AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = field(default_factory=lambda: os.getenv('DEBUG', 'true').lower() == 'true')
    ENV: str = field(default_factory=lambda: os.getenv('FLASK_ENV', 'development'))


@dataclass
class ServerConfig:
    """伺服器配置"""
    HOST: str = field(default_factory=lambda: os.getenv('HOST', '0.0.0.0'))
    PORT: int = field(default_factory=lambda: int(os.getenv('PORT', 5000)))
    WORKERS: int = field(default_factory=lambda: int(os.getenv('WORKERS', 1)))


@dataclass
class CORSConfig:
    """CORS 配置"""
    ALLOWED_ORIGINS: List[str] = field(default_factory=lambda: _parse_origins())


def _parse_origins() -> List[str]:
    """解析允許的來源"""
    origins = os.getenv('ALLOWED_ORIGINS', '*')
    if origins == '*':
        return ['*']
    return [origin.strip() for origin in origins.split(',')]


@dataclass
class PathConfig:
    """路徑配置"""
    BASE_DIR: str = field(default_factory=lambda: os.path.dirname(os.path.abspath(__file__)))
    UPLOAD_DIR: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'uploads'
    ))
    DATA_DIR: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'data'
    ))
    MODEL_DIR: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'models'
    ))
    
    def __post_init__(self):
        """確保必要目錄存在"""
        for dir_path in [self.UPLOAD_DIR, self.DATA_DIR, self.MODEL_DIR]:
            os.makedirs(dir_path, exist_ok=True)


@dataclass
class AIConfig:
    """AI 相關配置"""
    GEMINI_API_KEY: Optional[str] = field(default_factory=lambda: os.getenv('GEMINI_API_KEY'))
    GEMINI_MODEL: str = field(default_factory=lambda: os.getenv('GEMINI_MODEL', 'gemini-3-pro-preview'))
    MAX_VIDEO_DURATION: int = 10  # 秒
    RECOMMENDED_VIDEO_DURATION: int = 4  # 秒
    SUPPORTED_VIDEO_FORMATS: List[str] = field(default_factory=lambda: ['mp4', 'avi', 'mov', 'mkv'])


@dataclass
class SchedulerConfig:
    """排程器配置"""
    UPDATE_INTERVAL_HOURS: int = field(default_factory=lambda: int(os.getenv('UPDATE_INTERVAL_HOURS', 1)))
    ENABLED: bool = field(default_factory=lambda: os.getenv('SCHEDULER_ENABLED', 'true').lower() == 'true')


@dataclass
class Config:
    """主配置類別 - 聚合所有配置"""
    app: AppConfig = field(default_factory=AppConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    cors: CORSConfig = field(default_factory=CORSConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)


# 全域配置實例
config = Config()


def get_config() -> Config:
    """獲取配置實例"""
    return config
