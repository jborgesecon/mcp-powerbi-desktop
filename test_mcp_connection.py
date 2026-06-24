import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

# Import the server module
import mcp_server

class TestMCPConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Reset server connection state before each test
        mcp_server.current_connection = None

    @patch('mcp_server.detect_instances')
    @patch('mcp_server.XMLAConnection')
    async def test_single_instance_auto_bind(self, mock_xmla, mock_detect):
        # Simulate exactly one instance running on port 12345
        mock_detect.return_value = [{"port": 12345, "name": "PBI_1"}]
        
        # Mock XMLAConnection instance
        mock_conn_instance = MagicMock()
        mock_conn_instance.port = 12345
        mock_conn_instance.discover_database = AsyncMock()
        mock_xmla.return_value = mock_conn_instance
        
        # Mock the execute method of get_model_metadata
        with patch('mcp_server.get_model_metadata.execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = ["metadata_result"]
            
            # Call get_model_metadata without calling select_instance first
            res = await mcp_server.handle_call_tool("get_model_metadata", {})
            
            # Verify auto-binding was triggered
            mock_xmla.assert_called_once_with(port=12345)
            mock_conn_instance.discover_database.assert_awaited_once()
            mock_execute.assert_awaited_once_with({}, mock_conn_instance)
            self.assertEqual(res, ["metadata_result"])
            self.assertEqual(mcp_server.current_connection, mock_conn_instance)

    @patch('mcp_server.detect_instances')
    @patch('mcp_server.XMLAConnection')
    async def test_zero_instances_error(self, mock_xmla, mock_detect):
        # Simulate zero instances running
        mock_detect.return_value = []
        
        res = await mcp_server.handle_call_tool("get_model_metadata", {})
        
        # Verify clear error is returned
        self.assertEqual(len(res), 1)
        self.assertIn("Error: No running Power BI Desktop instances were found.", res[0].text)
        self.assertIsNone(mcp_server.current_connection)

    @patch('mcp_server.detect_instances')
    @patch('mcp_server.XMLAConnection')
    async def test_multiple_instances_error(self, mock_xmla, mock_detect):
        # Simulate two instances running
        mock_detect.return_value = [
            {"port": 12345, "name": "PBI_1"},
            {"port": 67890, "name": "PBI_2"}
        ]
        
        res = await mcp_server.handle_call_tool("get_model_metadata", {})
        
        # Verify disambiguation error is returned
        self.assertEqual(len(res), 1)
        self.assertIn("Multiple Power BI Desktop instances are running. Please call select_instance(port) explicitly or provide a port argument.", res[0].text)
        self.assertIsNone(mcp_server.current_connection)

    @patch('mcp_server.detect_instances')
    @patch('mcp_server.XMLAConnection')
    async def test_explicit_port_override(self, mock_xmla, mock_detect):
        # Even if multiple instances are running, passing explicit port should work
        mock_detect.return_value = [
            {"port": 12345, "name": "PBI_1"},
            {"port": 67890, "name": "PBI_2"}
        ]
        
        mock_conn_instance = MagicMock()
        mock_conn_instance.port = 67890
        mock_conn_instance.discover_database = AsyncMock()
        mock_xmla.return_value = mock_conn_instance
        
        with patch('mcp_server.get_model_metadata.execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = ["metadata_result"]
            
            res = await mcp_server.handle_call_tool("get_model_metadata", {"port": 67890})
            
            # Verify it bound directly to 67890
            mock_xmla.assert_called_once_with(port=67890)
            mock_conn_instance.discover_database.assert_awaited_once()
            mock_execute.assert_awaited_once_with({"port": 67890}, mock_conn_instance)
            self.assertEqual(res, ["metadata_result"])
            self.assertEqual(mcp_server.current_connection, mock_conn_instance)

    @patch('mcp_server.detect_instances')
    @patch('mcp_server.XMLAConnection')
    async def test_manual_select_and_reuse(self, mock_xmla, mock_detect):
        # 1. Call select_instance manually
        mock_conn_instance = MagicMock()
        mock_conn_instance.port = 9999
        mock_conn_instance.discover_database = AsyncMock()
        mock_xmla.return_value = mock_conn_instance
        
        with patch('mcp_server.select_instance.execute', new_callable=AsyncMock) as mock_select_exec:
            mock_select_exec.return_value = ["select_success"]
            select_res = await mcp_server.handle_call_tool("select_instance", {"port": 9999})
            
            self.assertEqual(select_res, ["select_success"])
            self.assertEqual(mcp_server.current_connection, mock_conn_instance)
            
        # 2. Call an operational tool and verify it reuses the connection without auto-discovery
        with patch('mcp_server.get_model_metadata.execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = ["metadata_result"]
            
            # Reset mocks to verify they are not called again for discovery
            mock_xmla.reset_mock()
            mock_detect.reset_mock()
            
            res = await mcp_server.handle_call_tool("get_model_metadata", {})
            
            mock_detect.assert_not_called()
            mock_xmla.assert_not_called()
            mock_execute.assert_awaited_once_with({}, mock_conn_instance)
            self.assertEqual(res, ["metadata_result"])

    @patch('mcp_server.detect_instances')
    @patch('mcp_server.XMLAConnection')
    async def test_new_tools_auto_bind(self, mock_xmla, mock_detect):
        # Verify the new tools can auto-bind connection correctly
        mock_detect.return_value = [{"port": 12345, "name": "PBI_1"}]
        mock_conn_instance = MagicMock()
        mock_conn_instance.port = 12345
        mock_conn_instance.discover_database = AsyncMock()
        mock_xmla.return_value = mock_conn_instance

        # Test list_table_columns auto-binds
        with patch('mcp_server.list_table_columns.execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ["cols_result"]
            res = await mcp_server.handle_call_tool("list_table_columns", {"table": "my_table"})
            mock_exec.assert_awaited_once_with({"table": "my_table"}, mock_conn_instance)
            self.assertEqual(res, ["cols_result"])

        # Test preview_table_data auto-binds
        with patch('mcp_server.preview_table_data.execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ["preview_result"]
            res = await mcp_server.handle_call_tool("preview_table_data", {"table": "my_table"})
            mock_exec.assert_awaited_once_with({"table": "my_table"}, mock_conn_instance)
            self.assertEqual(res, ["preview_result"])

        # Test inspect_table auto-binds
        with patch('mcp_server.inspect_table.execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ["inspect_result"]
            res = await mcp_server.handle_call_tool("inspect_table", {"table": "my_table"})
            mock_exec.assert_awaited_once_with({"table": "my_table"}, mock_conn_instance)
            self.assertEqual(res, ["inspect_result"])

        # Test get_calculated_columns auto-binds
        with patch('mcp_server.get_calculated_columns.execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ["calc_result"]
            res = await mcp_server.handle_call_tool("get_calculated_columns", {"table": "my_table"})
            mock_exec.assert_awaited_once_with({"table": "my_table"}, mock_conn_instance)
            self.assertEqual(res, ["calc_result"])

        # Test get_relationships auto-binds
        with patch('mcp_server.get_relationships.execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ["rels_result"]
            res = await mcp_server.handle_call_tool("get_relationships", {"table": "my_table"})
            mock_exec.assert_awaited_once_with({"table": "my_table"}, mock_conn_instance)
            self.assertEqual(res, ["rels_result"])

if __name__ == "__main__":
    unittest.main()
