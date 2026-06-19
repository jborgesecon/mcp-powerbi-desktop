import sys
import os
import re
import json
import urllib.request
import xml.etree.ElementTree as ET

def get_xmla_ports():
    pids = []
    try:
        import subprocess
        output = subprocess.check_output("tasklist /FI \"IMAGENAME eq msmdsrv.exe\" /FO CSV /NH", shell=True).decode('utf-8', errors='ignore')
        for line in output.strip().split('\n'):
            parts = line.split(',')
            if len(parts) >= 2:
                pid_str = parts[1].strip('"')
                if pid_str.isdigit():
                    pids.append(int(pid_str))
    except Exception as e:
        sys.stderr.write(f"Error getting PIDs: {e}\n")
    
    ports = []
    if not pids:
        return ports
        
    try:
        netstat_out = subprocess.check_output("netstat -ano", shell=True).decode('utf-8', errors='ignore')
        for line in netstat_out.strip().split('\n'):
            if "LISTENING" in line:
                for pid in pids:
                    if f" {pid}" in line or f"\t{pid}" in line or line.strip().endswith(f" {pid}"):
                        match = re.search(r'127\.0\.0\.1:(\d+)|\[::1\]:(\d+)', line)
                        if match:
                            port = int(next(p for p in match.groups() if p is not None))
                            if (pid, port) not in ports:
                                ports.append((pid, port))
    except Exception as e:
        sys.stderr.write(f"Error getting ports: {e}\n")
        
    return ports

def query_xmla(port, query, catalog=None):
    url = f"http://127.0.0.1:{port}/xmla"
    catalog_el = f"<Catalog>{catalog}</Catalog>" if catalog else ""
    soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <Execute xmlns="urn:schemas-microsoft-com:xml-analysis">
      <Command>
        <Statement>{query}</Statement>
      </Command>
      <Properties>
        <PropertyList>
          {catalog_el}
          <Format>Tabular</Format>
        </PropertyList>
      </Properties>
    </Execute>
  </soap:Body>
</soap:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": 'urn:schemas-microsoft-com:xml-analysis:Execute'
    }

    req = urllib.request.Request(url, data=soap_envelope.encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode('utf-8')
            return body, None
    except Exception as e:
        return None, str(e)

def parse_xml_rows(xml_str, target_tag):
    try:
        root = ET.fromstring(xml_str)
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'xmla': 'urn:schemas-microsoft-com:xml-analysis',
            'rowset': 'urn:schemas-microsoft-com:xml-analysis:rowset'
        }
        rows = root.findall('.//rowset:row', namespaces)
        results = []
        for row in rows:
            el = row.find(f'rowset:{target_tag}', namespaces)
            if el is not None and el.text:
                results.append(el.text)
        return results, None
    except Exception as e:
        return [], str(e)

def main():
    instances = []
    ports = get_xmla_ports()
    
    for pid, port in ports:
        catalog = "db"
        catalog_query = "SELECT [CATALOG_NAME] FROM $SYSTEM.DBSCHEMA_CATALOGS"
        xml_res, err = query_xmla(port, catalog_query)
        if err:
            instances.append({
                "pid": pid,
                "port": port,
                "error": f"Catalog discovery failed: {err}"
            })
            continue
            
        catalogs, parse_err = parse_xml_rows(xml_res, 'CATALOG_NAME')
        if catalogs:
            catalog = catalogs[0]
            
        tables_query = "SELECT [Dimension_Unique_Name] FROM $SYSTEM.MDSCHEMA_DIMENSIONS WHERE [Dimension_Is_Shared] = True"
        xml_res_tables, err = query_xmla(port, tables_query, catalog)
        if err:
            instances.append({
                "pid": pid,
                "port": port,
                "catalog": catalog,
                "error": f"Tables query failed: {err}"
            })
            continue
            
        unique_names, parse_err = parse_xml_rows(xml_res_tables, 'Dimension_Unique_Name')
        tables = []
        for name in unique_names:
            clean_name = name.strip("[]")
            if clean_name and clean_name not in tables:
                tables.append(clean_name)
                
        instances.append({
            "pid": pid,
            "port": port,
            "catalog": catalog,
            "tables_count": len(tables),
            "tables": tables
        })
        
    output = {
        "instances_count": len(instances),
        "instances": instances
    }
    print(json.dumps(output, indent=4))

if __name__ == "__main__":
    main()
