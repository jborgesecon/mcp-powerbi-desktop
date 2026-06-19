from powerbi.xmla_connection import XMLAConnection

class TMSLExecutor:
    def __init__(self, connection: XMLAConnection):
        self.connection = connection

    async def run_script(self, tmsl_script: str) -> dict:
        """Executes raw TMSL against the model."""
        return await self.connection.execute_xmla(tmsl_script)
