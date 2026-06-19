import socket

def main():
    port = 62903
    soap = '<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><Execute xmlns="urn:schemas-microsoft-com:xml-analysis"><Command><Statement>SELECT [CATALOG_NAME] FROM $SYSTEM.DBSCHEMA_CATALOGS</Statement></Command><Properties><PropertyList><Format>Tabular</Format></PropertyList></Properties></Execute></soap:Body></soap:Envelope>'
    
    request = (
        f"POST /xmla HTTP/1.1\r\n"
        f"Host: 127.0.0.1:{port}\r\n"
        f"Content-Type: text/xml; charset=utf-8\r\n"
        f"SOAPAction: \"urn:schemas-microsoft-com:xml-analysis:Execute\"\r\n"
        f"Content-Length: {len(soap)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
        f"{soap}"
    )
    
    print("Connecting to socket...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect(("127.0.0.1", port))
        print("Connected. Sending request...")
        s.sendall(request.encode('utf-8'))
        print("Request sent. Reading response...")
        response = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                print("Socket closed by remote.")
                break
            response += chunk
            print(f"Received chunk of {len(chunk)} bytes.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        s.close()
        
    print("\n--- RESPONSE ---")
    print(response.decode('utf-8', errors='ignore'))

if __name__ == "__main__":
    main()
