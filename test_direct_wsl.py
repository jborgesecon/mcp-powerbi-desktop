import urllib.request
import xml.etree.ElementTree as ET

def main():
    port = 62903
    url = f"http://127.0.0.1:{port}/xmla"
    print(f"Connecting to XMLA endpoint {url}...")
    
    # Simple DMV Query to list database catalogs
    query = "SELECT [CATALOG_NAME] FROM $SYSTEM.DBSCHEMA_CATALOGS"
    
    soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <Execute xmlns="urn:schemas-microsoft-com:xml-analysis">
      <Command>
        <Statement>{query}</Statement>
      </Command>
      <Properties>
        <PropertyList>
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
            print("\nResponse Received Successfully!")
            print(body[:1000]) # Print first 1000 chars of response
            
            # Parse XML
            root = ET.fromstring(body)
            # Find the CATALOG_NAME
            # SSAS XML namespaces
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'xmla': 'urn:schemas-microsoft-com:xml-analysis',
                'rowset': 'urn:schemas-microsoft-com:xml-analysis:rowset'
            }
            
            # Search for row elements
            rows = root.findall('.//rowset:row', namespaces)
            print(f"\nFound {len(rows)} catalogs:")
            for row in rows:
                cat_name = row.find('rowset:CATALOG_NAME', namespaces)
                if cat_name is not None:
                    print(f"  Catalog Name: {cat_name.text}")
    except Exception as e:
        print(f"\nConnection failed: {e}")

if __name__ == "__main__":
    main()
