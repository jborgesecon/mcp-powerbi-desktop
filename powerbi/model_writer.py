import json
from powerbi.xmla_connection import XMLAConnection

class ModelWriter:
    def __init__(self, connection: XMLAConnection):
        self.connection = connection

    async def upsert_measure(self, table: str, name: str, dax: str) -> dict:
        """Creates or updates a measure in the specified table."""
        # Use native TOM upsert via PowerShell if available
        if hasattr(self.connection, "has_powershell") and self.connection.has_powershell:
            return await self.connection.upsert_measure(table, name, dax)
        
        # Fallback to standard TMSL JSON script execution (fails for local desktop but kept for spec compliance/cloud fallback)
        tmsl_payload = {
            "createOrReplace": {
                "object": {
                    "database": self.connection.active_database,
                    "table": table,
                    "measure": name
                },
                "measure": {
                    "name": name,
                    "expression": dax
                }
            }
        }
        
        # Wrap TMSL JSON script as an XMLA command string
        tmsl_string = json.dumps(tmsl_payload)
        return await self.connection.execute_xmla(tmsl_string)
