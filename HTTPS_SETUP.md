# HTTPS Setup for Personal Use

## ✅ What Was Set Up

Self-signed SSL certificates for secure local access to your Intradyne system.

---

## 🔒 How to Use HTTPS

### Step 1: Generate Certificates (One-Time)

```bash
python scripts\generate_ssl_cert.py
```

This creates:
- `certs/cert.pem` - SSL certificate (valid 1 year)
- `certs/key.pem` - Private key

### Step 2: Start Services with HTTPS

**Option A - API Only:**
```bash
python scripts\start_api_https.py
```

**Option B - Both API + Dashboard:**
```bash
# Terminal 1 - API
python scripts\start_api_https.py

# Terminal 2 - Dashboard (HTTP is fine for localhost)
streamlit run src/interface/streamlit_app.py
```

### Step 3: Access Your Services

- **API**: https://localhost:8000
- **API Docs**: https://localhost:8000/docs
- **Dashboard**: http://localhost:8501 (or https if configured)

---

## ⚠️ Browser Security Warning

**You WILL see this warning - it's normal!**

```
Your connection is not private
Attackers might be trying to steal your information...
```

**This is expected** because you're using a self-signed certificate.

### How to Proceed:

**Chrome/Edge:**
1. Click "Advanced"
2. Click "Proceed to localhost (unsafe)"

**Firefox:**
1. Click "Advanced"
2. Click "Accept the Risk and Continue"

**Safari:**
1. Click "Show Details"
2. Click "visit this website"

---

## 🌐 Access from Other Devices (Phone/Tablet)

### On Your Local Network:

1. Find your PC's IP address:
   ```powershell
   ipconfig
   ```
   Look for "IPv4 Address" (e.g., `192.168.1.100`)

2. On your phone/tablet, visit:
   - API: `https://192.168.1.100:8000`
   - Dashboard: `http://192.168.1.100:8501`

3. Accept the security warning on your device

---

## 🔧 Configuration

### Update WebSocket URL

If using HTTPS, update `config/realtime_config.json`:

```json
{
  "websocket": {
    "url": "wss://localhost:8000/ws/trading-stream"
  }
}
```

Note: `wss://` instead of `ws://` for secure WebSocket

---

## 📋 Troubleshooting

### Certificate Expired?

Re-generate:
```bash
python scripts\generate_ssl_cert.py
```

### Can't Connect from Another Device?

1. Check Windows Firewall:
   - Open Windows Defender Firewall
   - Allow Python through firewall
   - Allow ports 8000 and 8501

2. Make sure services are bound to `0.0.0.0` not `127.0.0.1`

### Still Getting HTTP instead of HTTPS?

Make sure you're using:
- `https://` in the URL (not `http://`)
- `wss://` for WebSocket (not `ws://`)

---

## 🔒 Security Notes

### For Personal Use:
- ✅ Perfect for local development
- ✅ Safe for local network access
- ✅ Encrypts traffic between browser and server

### NOT Recommended For:
- ❌ Public internet access
- ❌ Production deployment
- ❌ Sharing with external users

**For production**, you would need:
- Real domain name
- Let's Encrypt certificate (free)
- Proper hosting (VPS/cloud)

---

## 📁 Files Created

- `scripts/generate_ssl_cert.py` - Certificate generator
- `scripts/start_api_https.py` - HTTPS API launcher
- `certs/cert.pem` - SSL certificate
- `certs/key.pem` - Private key

---

**Status:** ✅ Ready for HTTPS personal use!
