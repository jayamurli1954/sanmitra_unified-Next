"""
Phase 1: Foundation - MongoDB Configuration

Motor (async MongoDB driver) setup for flexible document storage.

This handles:
- MongoDB connection management
- Database and collection access
- Connection pooling
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging

from app.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

# Global MongoDB client and database
client: AsyncIOMotorClient = None
db: AsyncIOMotorDatabase = None


async def init_mongo():
    """
    Initialize MongoDB connection.

    Called during application startup.
    Creates client and database connections.
    """
    global client, db

    logger.info(f"Connecting to MongoDB: {settings.MONGODB_URL}")

    try:
        # Create async MongoDB client
        client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=settings.MONGO_SERVER_SELECTION_TIMEOUT_MS,
            connectTimeoutMS=settings.MONGO_CONNECT_TIMEOUT_MS,
        )

        # Get database
        db = client[settings.MONGO_DB_NAME]

        # Test connection
        await client.server_info()
        logger.info(f"✅ MongoDB connection successful (DB: {settings.MONGODB_DB_NAME})")

    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {str(e)}")
        raise


async def close_mongo():
    """
    Close MongoDB connection.

    Called during application shutdown.
    """
    global client

    if client:
        logger.info("Closing MongoDB connection...")
        client.close()
        logger.info("✅ MongoDB connection closed")


def get_collection(collection_name: str):
    """
    Get MongoDB collection by name.

    Use in services to access collections:
        collection = get_collection("mandir_donations")
        result = await collection.find_one({"_id": ObjectId(id)})

    Args:
        collection_name: Name of collection (e.g., "mandir_donations")

    Returns:
        AsyncIOMotorCollection for database operations

    Raises:
        RuntimeError: If MongoDB not initialized
    """
    if not db:
        raise RuntimeError("MongoDB not initialized. Call init_mongo() first.")

    return db[collection_name]


async def get_mongodb() -> AsyncIOMotorDatabase:
    """
    Get MongoDB database instance.

    For advanced operations needing full database access.

    Returns:
        AsyncIOMotorDatabase instance
    """
    if not db:
        raise RuntimeError("MongoDB not initialized. Call init_mongo() first.")

    return db


# Collection names (centralized)
class Collections:
    """Centralized collection names to prevent typos."""

    # Mandir (temple management)
    MANDIR_DONATIONS = "mandir_donations"
    MANDIR_SEVAS = "mandir_sevas"
    MANDIR_SEVA_BOOKINGS = "mandir_seva_bookings"
    MANDIR_DEVOTEES = "mandir_devotees"
    MANDIR_TEMPLES = "mandir_temples"
    MANDIR_INVENTORY_ITEMS = "mandir_inventory_items"
    MANDIR_BANK_ACCOUNTS = "mandir_bank_accounts"
    MANDIR_BANK_STATEMENTS = "mandir_bank_statements"
    MANDIR_BANK_STATEMENT_ENTRIES = "mandir_bank_statement_entries"
    MANDIR_UPI_PAYMENTS = "mandir_upi_payments"
    MANDIR_PANCHANG_SETTINGS = "mandir_panchang_settings"
    MANDIR_PUBLIC_PAYMENTS = "mandir_public_payments"
    MANDIR_ROLE_PERMISSIONS = "mandir_role_permissions"

    # Core
    CORE_USERS = "core_users"
    CORE_AUTH_REFRESH_TOKENS = "core_auth_refresh_tokens"
    CORE_TENANTS = "core_tenants"

    # Audit (critical)
    AUDIT_LOGS = "audit_logs"
