"""
Configuration Manager for Unified Sourcing Manager

This module loads configuration from environment variables and provides
type-safe configuration objects for the Unified Sourcing Manager system.
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class OpenAIConfig:
    """OpenAI API configuration"""
    api_key: str
    model: str = "gpt-4"
    temperature: float = 0.3
    max_tokens: int = 2000
    
    @classmethod
    def from_env(cls) -> 'OpenAIConfig':
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
        )

@dataclass
class LinkedInConfig:
    """LinkedIn API configuration"""
    api_key: str
    account_id: str
    base_url: str
    
    @classmethod
    def from_env(cls) -> 'LinkedInConfig':
        return cls(
            api_key=os.getenv("LINKEDIN_API_KEY", ""),
            account_id=os.getenv("LINKEDIN_ACCOUNT_ID", ""),
            base_url=os.getenv("LINKEDIN_BASE_URL", "https://api4.unipile.com:13447/api/v1")
        )

@dataclass
class MongoDBConfig:
    """MongoDB configuration"""
    username: str
    password: str
    host: str
    database: str
    collection: str
    
    @property
    def connection_string(self) -> str:
        """Generate MongoDB connection string"""
        return f"mongodb+srv://{self.username}:{self.password}@{self.host}/{self.database}"
    
    @classmethod
    def from_env(cls) -> 'MongoDBConfig':
        return cls(
            username=os.getenv("MONGO_USERNAME", ""),
            password=os.getenv("MONGO_PASSWORD", ""),
            host=os.getenv("MONGO_HOST", ""),
            database=os.getenv("MONGO_DATABASE", ""),
            collection=os.getenv("MONGO_COLLECTION", "projects")
        )

@dataclass
class UnifiedSourcingConfig:
    """Unified Sourcing Manager configuration"""
    enabled: bool = True
    max_retries: int = 3
    timeout_minutes: int = 30
    min_candidates: int = 5
    min_suitable: int = 3
    default_target_count: int = 50
    ai_decision_enabled: bool = True
    
    @classmethod
    def from_env(cls) -> 'UnifiedSourcingConfig':
        return cls(
            enabled=os.getenv("UNIFIED_SOURCING_ENABLED", "True").lower() == "true",
            max_retries=int(os.getenv("UNIFIED_SOURCING_MAX_RETRIES", "3")),
            timeout_minutes=int(os.getenv("UNIFIED_SOURCING_TIMEOUT_MINUTES", "30")),
            min_candidates=int(os.getenv("UNIFIED_SOURCING_MIN_CANDIDATES", "5")),
            min_suitable=int(os.getenv("UNIFIED_SOURCING_MIN_SUITABLE", "3")),
            default_target_count=int(os.getenv("UNIFIED_SOURCING_DEFAULT_TARGET_COUNT", "50")),
            ai_decision_enabled=os.getenv("UNIFIED_SOURCING_AI_DECISION_ENABLED", "True").lower() == "true"
        )

@dataclass
class DatabaseAgentConfig:
    """Database Agent configuration"""
    enabled: bool = True
    linkedin_url_unique_key: bool = True
    auto_deduplication: bool = True
    batch_size: int = 50
    
    @classmethod
    def from_env(cls) -> 'DatabaseAgentConfig':
        return cls(
            enabled=os.getenv("DATABASE_AGENT_ENABLED", "True").lower() == "true",
            linkedin_url_unique_key=os.getenv("DATABASE_AGENT_LINKEDIN_URL_UNIQUE_KEY", "True").lower() == "true",
            auto_deduplication=os.getenv("DATABASE_AGENT_AUTO_DEDUPLICATION", "True").lower() == "true",
            batch_size=int(os.getenv("DATABASE_AGENT_BATCH_SIZE", "50"))
        )

@dataclass
class CandidatePipelineConfig:
    """Candidate pipeline configuration"""
    search_enabled: bool = True
    evaluation_enabled: bool = True
    enrichment_enabled: bool = True
    profile_scraping_enabled: bool = False
    
    @classmethod
    def from_env(cls) -> 'CandidatePipelineConfig':
        return cls(
            search_enabled=os.getenv("CANDIDATE_SEARCH_ENABLED", "True").lower() == "true",
            evaluation_enabled=os.getenv("CANDIDATE_EVALUATION_ENABLED", "True").lower() == "true",
            enrichment_enabled=os.getenv("CANDIDATE_ENRICHMENT_ENABLED", "True").lower() == "true",
            profile_scraping_enabled=os.getenv("PROFILE_SCRAPING_ENABLED", "False").lower() == "true"
        )

@dataclass
class MonitoringConfig:
    """Performance and monitoring configuration"""
    performance_monitoring_enabled: bool = True
    audit_trail_enabled: bool = True
    metrics_collection_enabled: bool = True
    workflow_logging_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> 'MonitoringConfig':
        return cls(
            performance_monitoring_enabled=os.getenv("PERFORMANCE_MONITORING_ENABLED", "True").lower() == "true",
            audit_trail_enabled=os.getenv("AUDIT_TRAIL_ENABLED", "True").lower() == "true",
            metrics_collection_enabled=os.getenv("METRICS_COLLECTION_ENABLED", "True").lower() == "true",
            workflow_logging_level=os.getenv("WORKFLOW_LOGGING_LEVEL", "INFO")
        )

@dataclass
class AppConfig:
    """Complete application configuration"""
    debug: bool
    log_level: str
    max_retries: int
    request_timeout: int
    
    # Sub-configurations
    openai: OpenAIConfig
    linkedin: LinkedInConfig
    mongodb: MongoDBConfig
    unified_sourcing: UnifiedSourcingConfig
    database_agent: DatabaseAgentConfig
    candidate_pipeline: CandidatePipelineConfig
    monitoring: MonitoringConfig
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        return cls(
            debug=os.getenv("DEBUG", "True").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
            openai=OpenAIConfig.from_env(),
            linkedin=LinkedInConfig.from_env(),
            mongodb=MongoDBConfig.from_env(),
            unified_sourcing=UnifiedSourcingConfig.from_env(),
            database_agent=DatabaseAgentConfig.from_env(),
            candidate_pipeline=CandidatePipelineConfig.from_env(),
            monitoring=MonitoringConfig.from_env()
        )
    
    def validate(self) -> bool:
        """Validate configuration completeness"""
        issues = []
        
        # Check critical API keys
        if not self.openai.api_key or self.openai.api_key == "your_openai_api_key_here":
            issues.append("OPENAI_API_KEY is not configured")
        
        if not self.linkedin.api_key:
            issues.append("LINKEDIN_API_KEY is not configured")
        
        # Check MongoDB connection
        if not all([self.mongodb.username, self.mongodb.password, self.mongodb.host]):
            issues.append("MongoDB configuration is incomplete")
        
        # Check Unified Sourcing Manager settings
        if self.unified_sourcing.enabled:
            if self.unified_sourcing.max_retries < 1:
                issues.append("UNIFIED_SOURCING_MAX_RETRIES must be at least 1")
            
            if self.unified_sourcing.min_candidates < 1:
                issues.append("UNIFIED_SOURCING_MIN_CANDIDATES must be at least 1")
        
        if issues:
            print("❌ Configuration validation failed:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        
        print("✅ Configuration validation passed")
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for logging/debugging"""
        return {
            "app": {
                "debug": self.debug,
                "log_level": self.log_level,
                "max_retries": self.max_retries,
                "request_timeout": self.request_timeout
            },
            "openai": {
                "model": self.openai.model,
                "temperature": self.openai.temperature,
                "max_tokens": self.openai.max_tokens,
                "api_key_configured": bool(self.openai.api_key and self.openai.api_key != "your_openai_api_key_here")
            },
            "linkedin": {
                "base_url": self.linkedin.base_url,
                "api_key_configured": bool(self.linkedin.api_key),
                "account_id_configured": bool(self.linkedin.account_id)
            },
            "mongodb": {
                "host": self.mongodb.host,
                "database": self.mongodb.database,
                "collection": self.mongodb.collection,
                "credentials_configured": bool(self.mongodb.username and self.mongodb.password)
            },
            "unified_sourcing": {
                "enabled": self.unified_sourcing.enabled,
                "max_retries": self.unified_sourcing.max_retries,
                "timeout_minutes": self.unified_sourcing.timeout_minutes,
                "min_candidates": self.unified_sourcing.min_candidates,
                "min_suitable": self.unified_sourcing.min_suitable,
                "default_target_count": self.unified_sourcing.default_target_count,
                "ai_decision_enabled": self.unified_sourcing.ai_decision_enabled
            },
            "database_agent": {
                "enabled": self.database_agent.enabled,
                "linkedin_url_unique_key": self.database_agent.linkedin_url_unique_key,
                "auto_deduplication": self.database_agent.auto_deduplication,
                "batch_size": self.database_agent.batch_size
            },
            "candidate_pipeline": {
                "search_enabled": self.candidate_pipeline.search_enabled,
                "evaluation_enabled": self.candidate_pipeline.evaluation_enabled,
                "enrichment_enabled": self.candidate_pipeline.enrichment_enabled,
                "profile_scraping_enabled": self.candidate_pipeline.profile_scraping_enabled
            },
            "monitoring": {
                "performance_monitoring_enabled": self.monitoring.performance_monitoring_enabled,
                "audit_trail_enabled": self.monitoring.audit_trail_enabled,
                "metrics_collection_enabled": self.monitoring.metrics_collection_enabled,
                "workflow_logging_level": self.monitoring.workflow_logging_level
            }
        }


# Global configuration instance
config = AppConfig.from_env()


# Utility functions
def get_config() -> AppConfig:
    """Get the global configuration instance"""
    return config

def reload_config() -> AppConfig:
    """Reload configuration from environment variables"""
    global config
    load_dotenv(override=True)  # Reload .env file
    config = AppConfig.from_env()
    return config

def validate_config() -> bool:
    """Validate the current configuration"""
    return config.validate()

def print_config_summary():
    """Print a summary of the current configuration"""
    print("🔧 UNIFIED SOURCING MANAGER CONFIGURATION")
    print("=" * 60)
    
    config_dict = config.to_dict()
    
    print(f"📊 App Settings:")
    print(f"   Debug: {config_dict['app']['debug']}")
    print(f"   Log Level: {config_dict['app']['log_level']}")
    print(f"   Max Retries: {config_dict['app']['max_retries']}")
    
    print(f"\n🤖 OpenAI Configuration:")
    print(f"   Model: {config_dict['openai']['model']}")
    print(f"   Temperature: {config_dict['openai']['temperature']}")
    print(f"   API Key: {'✅ Configured' if config_dict['openai']['api_key_configured'] else '❌ Missing'}")
    
    print(f"\n🔗 LinkedIn Configuration:")
    print(f"   Base URL: {config_dict['linkedin']['base_url']}")
    print(f"   API Key: {'✅ Configured' if config_dict['linkedin']['api_key_configured'] else '❌ Missing'}")
    
    print(f"\n🗄️ MongoDB Configuration:")
    print(f"   Host: {config_dict['mongodb']['host']}")
    print(f"   Database: {config_dict['mongodb']['database']}")
    print(f"   Credentials: {'✅ Configured' if config_dict['mongodb']['credentials_configured'] else '❌ Missing'}")
    
    print(f"\n🚀 Unified Sourcing Manager:")
    print(f"   Enabled: {config_dict['unified_sourcing']['enabled']}")
    print(f"   AI Decisions: {config_dict['unified_sourcing']['ai_decision_enabled']}")
    print(f"   Max Retries: {config_dict['unified_sourcing']['max_retries']}")
    print(f"   Min Candidates: {config_dict['unified_sourcing']['min_candidates']}")
    
    print(f"\n🎯 Candidate Pipeline:")
    print(f"   Search: {config_dict['candidate_pipeline']['search_enabled']}")
    print(f"   Evaluation: {config_dict['candidate_pipeline']['evaluation_enabled']}")
    print(f"   Enrichment: {config_dict['candidate_pipeline']['enrichment_enabled']}")
    print(f"   Profile Scraping: {config_dict['candidate_pipeline']['profile_scraping_enabled']}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("🧪 Configuration Manager Test")
    print_config_summary()
    
    print("\n🔍 Validating configuration...")
    if validate_config():
        print("🎉 Configuration is ready for production!")
    else:
        print("⚠️ Configuration needs attention before production use.")