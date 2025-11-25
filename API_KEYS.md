# API Key Management Guide

## Overview

Secure API key management with encryption, validation, and rotation support.

---

## Features

### 1. Encrypted Storage
- **Algorithm**: Fernet (symmetric encryption)
- **Key Derivation**: PBKDF2 with SHA-256
- **Storage**: `~/.intradyne/keys.enc`
- **Permissions**: 600 (owner read/write only)

### 2. Environment Fallback
- Automatic fallback to environment variables
- No encryption required for testing
- Compatible with Docker/Kubernetes secrets

### 3. Key Rotation
- Update keys without downtime
- Maintains old password if applicable
- Audit trail with timestamps

---

## Usage

### Add API Keys (Encrypted)

```python
from src.security import get_key_manager

# Initialize with master password
manager = get_key_manager(master_password="your_secure_password")

# Add exchange keys
manager.add_exchange_keys(
    exchange='bitget',
    api_key='your_api_key',
    secret='your_secret',
    password='your_password'  # Optional
)
```

### Get API Keys

```python
# Retrieve keys
keys = manager.get_exchange_keys('bitget')

print(keys['api_key'])
print(keys['secret'])
print(keys['password'])  # May be None
```

### Validate Keys

```python
# Check if keys exist and are valid
is_valid = manager.validate_keys('bitget')

if is_valid:
    print("Keys are valid")
else:
    print("Keys missing or invalid")
```

### Rotate Keys

```python
# Update keys
manager.encrypted_manager.rotate_keys(
    exchange='bitget',
    new_api_key='new_key',
    new_secret='new_secret'
)
```

---

## Environment Variables

### Format

```env
# Generic (works for any exchange)
EXCHANGE_API_KEY=your_api_key
EXCHANGE_SECRET=your_secret
EXCHANGE_PASSWORD=your_password

# Exchange-specific (higher priority)
BITGET_API_KEY=bitget_key
BITGET_SECRET=bitget_secret
BITGET_PASSWORD=bitget_password

BINANCE_API_KEY=binance_key
BINANCE_SECRET=binance_secret
```

### Priority

1. Exchange-specific env vars (`BITGET_API_KEY`)
2. Generic env vars (`EXCHANGE_API_KEY`)
3. Encrypted storage

---

## Master Password

### Set Master Password

```bash
# Environment variable
export MASTER_PASSWORD=your_secure_password

# Or in .env file
MASTER_PASSWORD=your_secure_password
```

### Generate Strong Password

```python
import secrets
import string

def generate_password(length=32):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

password = generate_password()
print(password)
```

---

## Security Best Practices

### 1. Master Password
- Use strong, unique password
- Store in secure location (password manager)
- Never commit to version control
- Rotate periodically

### 2. API Keys
- Use read-only keys for backtesting
- Use trading keys only for live trading
- Enable IP whitelist on exchange
- Set withdrawal restrictions

### 3. Storage
- Encrypted file has 600 permissions
- Stored in user home directory
- Not accessible by other users
- Backed up securely

### 4. Environment Variables
- Use for Docker/Kubernetes
- Never log or print
- Clear after use in scripts
- Use secrets management in production

---

## Integration Examples

### With Paper Trader

```python
from src.trading.paper_trader import PaperTrader
from src.security import get_key_manager

# Get keys
manager = get_key_manager()
keys = manager.get_exchange_keys('bitget')

# Initialize trader
trader = PaperTrader(initial_capital=10000)

# Connect with keys
trader.connect_exchange(
    exchange_name='bitget',
    api_key=keys['api_key'],
    secret=keys['secret'],
    password=keys.get('password')
)
```

### With CCXT

```python
import ccxt
from src.security import get_key_manager

# Get keys
manager = get_key_manager()
keys = manager.get_exchange_keys('bitget')

# Create exchange instance
exchange = ccxt.bitget({
    'apiKey': keys['api_key'],
    'secret': keys['secret'],
    'password': keys.get('password'),
    'enableRateLimit': True
})

# Test connection
balance = exchange.fetch_balance()
```

---

## Docker Integration

### Using Environment Variables

```yaml
# docker-compose.yml
services:
  intradyne:
    environment:
      - EXCHANGE_API_KEY=${EXCHANGE_API_KEY}
      - EXCHANGE_SECRET=${EXCHANGE_SECRET}
    env_file:
      - .env
```

### Using Docker Secrets

```yaml
# docker-compose.yml
services:
  intradyne:
    secrets:
      - exchange_api_key
      - exchange_secret

secrets:
  exchange_api_key:
    file: ./secrets/api_key.txt
  exchange_secret:
    file: ./secrets/secret.txt
```

---

## Kubernetes Integration

### Create Secret

```bash
kubectl create secret generic intradyne-api-keys \
  --from-literal=api-key='your_api_key' \
  --from-literal=secret='your_secret'
```

### Use in Deployment

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: intradyne
spec:
  containers:
  - name: intradyne
    env:
    - name: EXCHANGE_API_KEY
      valueFrom:
        secretKeyRef:
          name: intradyne-api-keys
          key: api-key
    - name: EXCHANGE_SECRET
      valueFrom:
        secretKeyRef:
          name: intradyne-api-keys
          key: secret
```

---

## Troubleshooting

### Keys Not Found

```python
# Check available exchanges
manager = get_key_manager()
exchanges = manager.list_available_exchanges()
print(f"Available: {exchanges}")

# Validate specific exchange
is_valid = manager.validate_keys('bitget')
print(f"Bitget valid: {is_valid}")
```

### Decryption Failed

- Check master password is correct
- Verify keys file exists: `~/.intradyne/keys.enc`
- Try removing and re-adding keys

### Environment Variables Not Working

```python
import os

# Check if set
print(os.getenv('EXCHANGE_API_KEY'))
print(os.getenv('BITGET_API_KEY'))

# Load from .env file
from dotenv import load_dotenv
load_dotenv()
```

---

## CLI Tool (Optional)

### Manage Keys from Command Line

```bash
# Add keys
python scripts/manage_keys.py add bitget

# List exchanges
python scripts/manage_keys.py list

# Rotate keys
python scripts/manage_keys.py rotate bitget

# Remove keys
python scripts/manage_keys.py remove bitget
```

---

## Security Checklist

- [ ] Strong master password set
- [ ] Master password stored securely
- [ ] API keys have appropriate permissions
- [ ] IP whitelist enabled on exchange
- [ ] Withdrawal restrictions set
- [ ] Keys file has 600 permissions
- [ ] Keys not committed to git
- [ ] Environment variables secured
- [ ] Regular key rotation scheduled

---

**🔐 Secure API key management complete!**
