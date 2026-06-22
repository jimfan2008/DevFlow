"""
GBM AI Agent HR - 配置模块
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    APP_NAME: str = "GBM AI Agent HR"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://hr_user:hr_password@localhost:3306/gbm_hr_db"
    DATABASE_ECHO: bool = False
    
    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # MinIO 对象存储配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "gbm-hr-files"
    
    # JWT 配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8小时
    
    # 允许的来源
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:3000,http://localhost:8000"
    
    # AI 服务配置
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4"
    
    OCR_SERVICE_URL: str = "http://localhost:8001"
    FACE_RECOGNITION_SERVICE_URL: str = "http://localhost:8002"
    
    # 消息队列配置
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    
    # 安全配置
    PASSWORD_SALT: str = "your-password-salt-change-in-production"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例）"""
    return Settings()

settings = get_settings()
