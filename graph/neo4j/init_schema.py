import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "sarplatform123")

def init_schema():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # Create uniqueness constraints
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Account) REQUIRE a.account_id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Transaction) REQUIRE t.transaction_id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:SARCase) REQUIRE s.case_id IS UNIQUE")
        
        # Create indexes
        session.run("CREATE INDEX IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (s:SARCase) ON (s.risk_score)")
        
        # Optional: AuditEvent
        session.run("CREATE INDEX IF NOT EXISTS FOR (a:AuditEvent) ON (a.timestamp)")
    
    driver.close()
    print("Schema initialized")

if __name__ == "__main__":
    init_schema()
