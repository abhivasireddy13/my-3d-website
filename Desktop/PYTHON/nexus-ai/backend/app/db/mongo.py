from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

_client = AsyncIOMotorClient(settings.MONGO_URL)
mongo_db = _client["nexus"]

raw_uploads = mongo_db["raw_uploads"]
workflow_logs = mongo_db["workflow_logs"]
validation_errors = mongo_db["validation_errors"]
