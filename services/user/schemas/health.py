from pydantic import BaseModel
from typing import Dict, List, Optional

class DependencyStatus(BaseModel):
    status: str
    services: Dict[str, bool]

class ConfigurationStatus(BaseModel):
    status: str
    issues: List[str]

class DatabaseStatus(BaseModel):
    status: str
    response_time_ms: Optional[float] = None
    connected: bool
    error: Optional[str] = None

class PerformanceStatus(BaseModel):
    total_check_time_ms: float

class ReadinessChecks(BaseModel):
    database: DatabaseStatus
    configuration: ConfigurationStatus
    dependencies: DependencyStatus

class ReadinessStatus(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    environment: str
    checks: ReadinessChecks
    performance: PerformanceStatus 