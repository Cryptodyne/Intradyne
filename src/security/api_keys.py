"""
Secure API Key Management
Handles encryption, storage, and validation of API keys
"""

import os
import json
import base64
from typing import Dict, Optional
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import logging

class APIKeyManager:
    """
    Secure API key management with encryption.
    Stores keys encrypted at rest.
    """
    
    def __init__(self, master_password: str = None):
        """
        Initialize API key manager.
        
        Args:
            master_password: Master password for encryption
        """
        self.logger = logging.getLogger("APIKeyManager")
        self.keys_file = Path.home() / '.intradyne' / 'keys.enc'
        self.keys_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Get master password from env or parameter
        self.master_password = master_password or os.getenv('MASTER_PASSWORD', 'default_password_change_me')
        
        # Generate encryption key from master password
        self.cipher = self._create_cipher()
        
        # Load existing keys
        self.keys: Dict[str, Dict] = self._load_keys()
    
    def _create_cipher(self) -> Fernet:
        """Create Fernet cipher from master password"""
        # Derive key from password
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'intradyne_salt_v1',  # In production, use random salt
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_password.encode()))
        return Fernet(key)
    
    def _load_keys(self) -> Dict:
        """Load encrypted keys from file"""
        if not self.keys_file.exists():
            return {}
        
        try:
            with open(self.keys_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        
        except Exception as e:
            self.logger.error(f"Failed to load keys: {e}")
            return {}
    
    def _save_keys(self):
        """Save encrypted keys to file"""
        try:
            # Encrypt data
            data = json.dumps(self.keys).encode()
            encrypted_data = self.cipher.encrypt(data)
            
            # Save to file
            with open(self.keys_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set restrictive permissions (Unix-like systems)
            try:
                os.chmod(self.keys_file, 0o600)
            except:
                pass  # Windows doesn't support chmod
            
            self.logger.info("Keys saved successfully")
        
        except Exception as e:
            self.logger.error(f"Failed to save keys: {e}")
            raise
    
    def add_exchange_keys(self, exchange: str, api_key: str, 
                         secret: str, password: str = None):
        """
        Add exchange API keys.
        
        Args:
            exchange: Exchange name (e.g., 'bitget', 'binance')
            api_key: API key
            secret: API secret
            password: Optional password/passphrase
        """
        self.keys[exchange] = {
            'api_key': api_key,
            'secret': secret,
            'password': password,
            'created_at': str(Path.ctime(Path.cwd()))
        }
        
        self._save_keys()
        self.logger.info(f"Added keys for {exchange}")
    
    def get_exchange_keys(self, exchange: str) -> Optional[Dict]:
        """
        Get exchange API keys.
        
        Args:
            exchange: Exchange name
        
        Returns:
            Dictionary with api_key, secret, password
        """
        return self.keys.get(exchange)
    
    def remove_exchange_keys(self, exchange: str):
        """Remove exchange API keys"""
        if exchange in self.keys:
            del self.keys[exchange]
            self._save_keys()
            self.logger.info(f"Removed keys for {exchange}")
    
    def list_exchanges(self) -> list:
        """List exchanges with stored keys"""
        return list(self.keys.keys())
    
    def validate_keys(self, exchange: str) -> bool:
        """
        Validate that keys exist and are not empty.
        
        Args:
            exchange: Exchange name
        
        Returns:
            True if keys are valid
        """
        keys = self.get_exchange_keys(exchange)
        
        if not keys:
            return False
        
        if not keys.get('api_key') or not keys.get('secret'):
            return False
        
        return True
    
    def rotate_keys(self, exchange: str, new_api_key: str, new_secret: str):
        """
        Rotate API keys for an exchange.
        
        Args:
            exchange: Exchange name
            new_api_key: New API key
            new_secret: New API secret
        """
        if exchange not in self.keys:
            raise ValueError(f"No keys found for {exchange}")
        
        # Keep old password if exists
        old_password = self.keys[exchange].get('password')
        
        self.add_exchange_keys(exchange, new_api_key, new_secret, old_password)
        self.logger.info(f"Rotated keys for {exchange}")


class EnvironmentKeyLoader:
    """
    Load API keys from environment variables.
    Fallback when encrypted storage is not available.
    """
    
    @staticmethod
    def get_exchange_keys(exchange: str) -> Optional[Dict]:
        """
        Get exchange keys from environment variables.
        
        Expected format:
        - {EXCHANGE}_API_KEY
        - {EXCHANGE}_SECRET
        - {EXCHANGE}_PASSWORD (optional)
        
        Args:
            exchange: Exchange name
        
        Returns:
            Dictionary with keys or None
        """
        prefix = exchange.upper()
        
        api_key = os.getenv(f'{prefix}_API_KEY') or os.getenv('EXCHANGE_API_KEY')
        secret = os.getenv(f'{prefix}_SECRET') or os.getenv('EXCHANGE_SECRET')
        password = os.getenv(f'{prefix}_PASSWORD') or os.getenv('EXCHANGE_PASSWORD')
        
        if not api_key or not secret:
            return None
        
        return {
            'api_key': api_key,
            'secret': secret,
            'password': password
        }
    
    @staticmethod
    def validate_keys(exchange: str) -> bool:
        """Validate environment keys exist"""
        keys = EnvironmentKeyLoader.get_exchange_keys(exchange)
        return keys is not None


class SecureKeyManager:
    """
    Unified key manager with multiple backends.
    Tries encrypted storage first, falls back to environment variables.
    """
    
    def __init__(self, master_password: str = None, use_encryption: bool = True):
        """
        Initialize secure key manager.
        
        Args:
            master_password: Master password for encryption
            use_encryption: Whether to use encrypted storage
        """
        self.use_encryption = use_encryption
        self.logger = logging.getLogger("SecureKeyManager")
        
        if use_encryption:
            try:
                self.encrypted_manager = APIKeyManager(master_password)
                self.logger.info("Using encrypted key storage")
            except Exception as e:
                self.logger.warning(f"Encrypted storage failed: {e}, using environment")
                self.use_encryption = False
    
    def get_exchange_keys(self, exchange: str) -> Optional[Dict]:
        """
        Get exchange keys from best available source.
        
        Priority:
        1. Encrypted storage
        2. Environment variables
        
        Args:
            exchange: Exchange name
        
        Returns:
            Dictionary with keys or None
        """
        # Try encrypted storage first
        if self.use_encryption:
            keys = self.encrypted_manager.get_exchange_keys(exchange)
            if keys:
                self.logger.debug(f"Loaded {exchange} keys from encrypted storage")
                return keys
        
        # Fallback to environment
        keys = EnvironmentKeyLoader.get_exchange_keys(exchange)
        if keys:
            self.logger.debug(f"Loaded {exchange} keys from environment")
            return keys
        
        self.logger.warning(f"No keys found for {exchange}")
        return None
    
    def add_exchange_keys(self, exchange: str, api_key: str, 
                         secret: str, password: str = None):
        """Add exchange keys to encrypted storage"""
        if not self.use_encryption:
            raise RuntimeError("Encrypted storage not available")
        
        self.encrypted_manager.add_exchange_keys(exchange, api_key, secret, password)
    
    def validate_keys(self, exchange: str) -> bool:
        """Validate keys exist"""
        keys = self.get_exchange_keys(exchange)
        return keys is not None
    
    def list_available_exchanges(self) -> list:
        """List exchanges with available keys"""
        exchanges = set()
        
        # From encrypted storage
        if self.use_encryption:
            exchanges.update(self.encrypted_manager.list_exchanges())
        
        # From environment
        for exchange in ['bitget', 'binance', 'okx', 'bybit']:
            if EnvironmentKeyLoader.validate_keys(exchange):
                exchanges.add(exchange)
        
        return sorted(list(exchanges))


# Global instance
_key_manager: Optional[SecureKeyManager] = None

def get_key_manager(master_password: str = None) -> SecureKeyManager:
    """
    Get global key manager instance.
    
    Args:
        master_password: Master password for encryption
    
    Returns:
        SecureKeyManager instance
    """
    global _key_manager
    
    if _key_manager is None:
        _key_manager = SecureKeyManager(master_password)
    
    return _key_manager
