"""
Generate Self-Signed SSL Certificates for Personal Use
Creates certificates for HTTPS on localhost and local network.
"""

import os
from pathlib import Path
from datetime import datetime, timedelta

def generate_self_signed_cert():
    """Generate self-signed certificate for personal use."""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        print("❌ cryptography library not found")
        print("Installing...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'cryptography'])
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
    
    print("🔒 Generating Self-Signed SSL Certificate for Personal Use...")
    print()
    
    # Create certs directory
    cert_dir = Path("certs")
    cert_dir.mkdir(exist_ok=True)
    
    # Generate private key
    print("1. Generating private key...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Get local IP for certificate
    import socket
    import ipaddress
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "127.0.0.1"
    
    print(f"   Hostname: {hostname}")
    print(f"   Local IP: {local_ip}")
    print()
    
    # Create certificate
    print("2. Creating certificate...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Personal"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Intradyne"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)  # Valid for 1 year
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("*.localhost"),
            x509.DNSName(hostname),
            x509.IPAddress(ipaddress.IPv4Address(local_ip)),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256(), default_backend())
    
    # Write private key
    key_file = cert_dir / "key.pem"
    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    print(f"   ✅ Private key saved: {key_file}")
    
    # Write certificate
    cert_file = cert_dir / "cert.pem"
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    print(f"   ✅ Certificate saved: {cert_file}")
    print()
    
    print("✅ SSL Certificate Generated Successfully!")
    print()
    print("📋 Certificate Details:")
    print(f"   Valid for: 1 year (until {(datetime.utcnow() + timedelta(days=365)).strftime('%Y-%m-%d')})")
    print(f"   Common Name: localhost")
    print(f"   Also valid for: {hostname}, {local_ip}")
    print()
    print("🌐 You can now access your services via:")
    print(f"   - https://localhost:8000 (API)")
    print(f"   - https://localhost:8501 (Dashboard)")
    print(f"   - https://{local_ip}:8000 (API from other devices)")
    print(f"   - https://{local_ip}:8501 (Dashboard from other devices)")
    print()
    print("⚠️  Note: Browsers will show 'Not Secure' warning.")
    print("   This is normal for self-signed certificates.")
    print("   Click 'Advanced' → 'Proceed' to continue.")
    print()
    
    return str(cert_file), str(key_file)


if __name__ == "__main__":
    cert_file, key_file = generate_self_signed_cert()
    
    print("=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print()
    print("1. Restart your API server with HTTPS:")
    print("   python scripts/start_api_https.py")
    print()
    print("2. Access your dashboard:")
    print("   https://localhost:8501")
    print()
    print("3. Trust the certificate in your browser when prompted")
    print()
