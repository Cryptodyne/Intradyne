"""
Start FastAPI with HTTPS (Self-Signed Certificate)
For personal/local use only.
"""

import uvicorn
import os
from pathlib import Path

def main():
    # Check if certificates exist
    cert_file = Path("certs/cert.pem")
    key_file = Path("certs/key.pem")
    
    if not cert_file.exists() or not key_file.exists():
        print("❌ SSL certificates not found!")
        print("   Generating them now...")
        print()
        
        import subprocess
        subprocess.run(["python", "scripts/generate_ssl_cert.py"])
        
        if not cert_file.exists():
            print("Failed to generate certificates!")
            return
    
    print("=" * 70)
    print("🔒 Starting Intradyne API with HTTPS")
    print("=" * 70)
    print()
    print("✅ Using self-signed certificates")
    print(f"   Certificate: {cert_file}")
    print(f"   Private Key: {key_file}")
    print()
    print("🌐 API will be available at:")
    print("   - https://localhost:8000")
    print("   - https://localhost:8000/docs (API Documentation)")
    print()
    print("⚠️  Your browser will show a security warning.")
    print("   Click 'Advanced' → 'Proceed to localhost' to continue.")
    print()
    print("=" * 70)
    print()
    
    # Start Uvicorn with SSL
    uvicorn.run(
        "src.api.api_server:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile=str(key_file),
        ssl_certfile=str(cert_file),
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
