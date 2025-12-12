from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

class Database:
    client: AsyncIOMotorClient = None

    def connect(self):
        self.client = AsyncIOMotorClient(settings.mongodb_url)

    def close(self):
        if self.client:
            self.client.close()

    def get_master_db(self):
        return self.client[settings.master_database_name]

    def get_org_db(self, collection_name: str):
        # In this design, we are using dynamic collections within the same DB or separate DBs?
        # Requirement: "Dynamically create a new Mongo collection specifically for the organization. Example collection name pattern: org_<organization_name>"
        # "Maintain a Master Database for global metadata and create dynamic collections for each organization."
        # It's slightly ambiguous if "dynamic collections" means collections in the Master DB or a separate DB.
        # "create dynamic collections for each organization" usually implies collections in the same DB if not specified "dynamic databases".
        # However, "Connection details for each dynamic database" in Technical Requirements A implies dynamic databases?
        # Let's re-read: "Maintain a Master Database ... and create dynamic collections for each organization."
        # Requirement 1: "Dynamically create a new Mongo collection ... Example collection name pattern: org_<organization_name>"
        # This strongly suggests collections in the SAME database (or a specific tenant database).
        # Let's assume for MVP all org collections live in the SAME database as master or a specific 'tenants' database.
        # But wait, "Store ... Connection details (if required)" in 1.
        # "Technical Requirements A. Master Database Should store: ... Connection details for each dynamic database" -> This contradicts "dynamic collections".
        # Let's stick to "Dynamic Collection" as per the requirement 1 & 3 "Dynamically handle the new collection creation".
        # I will implement `get_org_collection` which returns a collection from the default DB (or master DB).
        # To avoid cluttering Master DB, I might use a single DB for everything, or Master DB + Tenants DB.
        # Given "org_<organization_name>" pattern, it's safer to put them in the same DB or a dedicated 'tenants' DB.
        # Let's put them in the 'master_db' for simplicity unless 'Connection details' implies sharding/separate clusters.
        # Since I am using local mongo, I will put everything in `master_database_name` for now, or maybe `tenants_db`.
        # Let's just use the `master_database_name` for everything to keep it simple as per "Example collection name pattern: org_<organization_name>".
        
        return self.client[settings.master_database_name][collection_name]

db = Database()
