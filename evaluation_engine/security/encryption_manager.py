"""
Data Encryption Manager for Data in Transit and at Rest

Provides comprehensive encryption capabilities with key management.
"""

import os
import base64
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Union, Tuple
from dataclasses import dataclass
from pathlib import Path
import hashlib
import secrets

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import ssl

try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False

logger = logging.getLogger(__name__)

@dataclass
class EncryptionKey:
    """Represents an encryption key with metadata"""
    key_id: str
    key_type: str  # 'symmetric', 'asymmetric_private', 'asymmetric_public'
    algorithm: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class EncryptedData:
    """Represents encrypted data with metadata"""
    data: bytes
    key_id: str
    algorithm: str
    iv: Optional[bytes] = None
    tag: Optional[bytes] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class KeyManager:
    """Manages encryption keys with rotation and lifecycle"""
    
    def __init__(self, key_store_path: str = "security/keys"):
        self.key_store_path = Path(key_store_path)
        self.key_store_path.mkdir(parents=True, exist_ok=True)
        self.keys: Dict[str, EncryptionKey] = {}
        self.key_data: Dict[str, bytes] = {}
        self._load_keys()
    
    def _load_keys(self):
        """Load keys from secure storage"""
        key_index_file = self.key_store_path / "key_index.json"
        if key_index_file.exists():
            try:
                with open(key_index_file, 'r') as f:
                    key_index = json.load(f)
                
                for key_id, key_info in key_index.items():
                    key_file = self.key_store_path / f"{key_id}.key"
                    if key_file.exists():
                        with open(key_file, 'rb') as f:
                            key_data = f.read()
                        
                        self.keys[key_id] = EncryptionKey(
                            key_id=key_id,
                            key_type=key_info['key_type'],
                            algorithm=key_info['algorithm'],
                            created_at=datetime.fromisoformat(key_info['created_at']),
                            expires_at=datetime.fromisoformat(key_info['expires_at']) if key_info.get('expires_at') else None,
                            is_active=key_info.get('is_active', True),
                            metadata=key_info.get('metadata', {})
                        )
                        self.key_data[key_id] = key_data
                        
            except Exception as e:
                logger.error(f"Failed to load keys: {e}")
    
    def _save_keys(self):
        """Save keys to secure storage"""
        try:
            key_index = {}
            for key_id, key in self.keys.items():
                key_index[key_id] = {
                    'key_type': key.key_type,
                    'algorithm': key.algorithm,
                    'created_at': key.created_at.isoformat(),
                    'expires_at': key.expires_at.isoformat() if key.expires_at else None,
                    'is_active': key.is_active,
                    'metadata': key.metadata
                }
                
                # Save key data
                key_file = self.key_store_path / f"{key_id}.key"
                with open(key_file, 'wb') as f:
                    f.write(self.key_data[key_id])
                
                # Set restrictive permissions
                os.chmod(key_file, 0o600)
            
            # Save key index
            key_index_file = self.key_store_path / "key_index.json"
            with open(key_index_file, 'w') as f:
                json.dump(key_index, f, indent=2)
            
            os.chmod(key_index_file, 0o600)
            
        except Exception as e:
            logger.error(f"Failed to save keys: {e}")
    
    def generate_symmetric_key(self, algorithm: str = "AES-256-GCM", 
                             expires_in_days: Optional[int] = 365) -> str:
        """Generate a new symmetric encryption key"""
        key_id = secrets.token_hex(16)
        
        if algorithm == "AES-256-GCM":
            key_data = secrets.token_bytes(32)  # 256 bits
        elif algorithm == "ChaCha20-Poly1305":
            key_data = secrets.token_bytes(32)  # 256 bits
        elif algorithm == "Fernet":
            key_data = Fernet.generate_key()
        else:
            raise ValueError(f"Unsupported symmetric algorithm: {algorithm}")
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        encryption_key = EncryptionKey(
            key_id=key_id,
            key_type="symmetric",
            algorithm=algorithm,
            created_at=datetime.utcnow(),
            expires_at=expires_at
        )
        
        self.keys[key_id] = encryption_key
        self.key_data[key_id] = key_data
        self._save_keys()
        
        logger.info(f"Generated symmetric key {key_id} with algorithm {algorithm}")
        return key_id
    
    def generate_asymmetric_keypair(self, algorithm: str = "RSA-2048",
                                  expires_in_days: Optional[int] = 365) -> Tuple[str, str]:
        """Generate asymmetric key pair"""
        if algorithm == "RSA-2048":
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            public_key = private_key.public_key()
            
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
        else:
            raise ValueError(f"Unsupported asymmetric algorithm: {algorithm}")
        
        private_key_id = secrets.token_hex(16)
        public_key_id = secrets.token_hex(16)
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Store private key
        private_encryption_key = EncryptionKey(
            key_id=private_key_id,
            key_type="asymmetric_private",
            algorithm=algorithm,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            metadata={"public_key_id": public_key_id}
        )
        
        # Store public key
        public_encryption_key = EncryptionKey(
            key_id=public_key_id,
            key_type="asymmetric_public",
            algorithm=algorithm,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            metadata={"private_key_id": private_key_id}
        )
        
        self.keys[private_key_id] = private_encryption_key
        self.keys[public_key_id] = public_encryption_key
        self.key_data[private_key_id] = private_pem
        self.key_data[public_key_id] = public_pem
        self._save_keys()
        
        logger.info(f"Generated asymmetric keypair: private={private_key_id}, public={public_key_id}")
        return private_key_id, public_key_id
    
    def get_key(self, key_id: str) -> Optional[Tuple[EncryptionKey, bytes]]:
        """Get key by ID"""
        if key_id in self.keys and key_id in self.key_data:
            key = self.keys[key_id]
            if key.is_active and (not key.expires_at or key.expires_at > datetime.utcnow()):
                return key, self.key_data[key_id]
        return None
    
    def rotate_key(self, old_key_id: str) -> str:
        """Rotate an encryption key"""
        old_key_info = self.keys.get(old_key_id)
        if not old_key_info:
            raise ValueError(f"Key {old_key_id} not found")
        
        # Generate new key with same algorithm
        if old_key_info.key_type == "symmetric":
            new_key_id = self.generate_symmetric_key(old_key_info.algorithm)
        else:
            raise ValueError("Asymmetric key rotation not implemented")
        
        # Deactivate old key
        old_key_info.is_active = False
        self._save_keys()
        
        logger.info(f"Rotated key {old_key_id} to {new_key_id}")
        return new_key_id
    
    def list_keys(self, active_only: bool = True) -> Dict[str, EncryptionKey]:
        """List all keys"""
        if active_only:
            return {k: v for k, v in self.keys.items() if v.is_active}
        return self.keys.copy()

class EncryptionManager:
    """Comprehensive encryption manager for data in transit and at rest"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.key_manager = KeyManager(self.config.get('key_store_path', 'security/keys'))
        self.default_algorithm = self.config.get('default_algorithm', 'AES-256-GCM')
        
        # Initialize default keys if none exist
        self._initialize_default_keys()
    
    def _initialize_default_keys(self):
        """Initialize default encryption keys"""
        active_keys = self.key_manager.list_keys(active_only=True)
        
        # Ensure we have at least one symmetric key
        symmetric_keys = [k for k, v in active_keys.items() if v.key_type == "symmetric"]
        if not symmetric_keys:
            self.key_manager.generate_symmetric_key(self.default_algorithm)
            logger.info("Generated default symmetric encryption key")
        
        # Ensure we have at least one asymmetric keypair
        asymmetric_keys = [k for k, v in active_keys.items() if v.key_type == "asymmetric_private"]
        if not asymmetric_keys:
            self.key_manager.generate_asymmetric_keypair()
            logger.info("Generated default asymmetric keypair")
    
    def encrypt_data(self, data: Union[str, bytes], key_id: Optional[str] = None,
                    algorithm: Optional[str] = None) -> EncryptedData:
        """Encrypt data using specified or default key"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Select key
        if not key_id:
            # Use first available symmetric key
            active_keys = self.key_manager.list_keys(active_only=True)
            symmetric_keys = [k for k, v in active_keys.items() if v.key_type == "symmetric"]
            if not symmetric_keys:
                raise ValueError("No symmetric keys available")
            key_id = symmetric_keys[0]
        
        key_info = self.key_manager.get_key(key_id)
        if not key_info:
            raise ValueError(f"Key {key_id} not found or expired")
        
        key, key_data = key_info
        algorithm = algorithm or key.algorithm
        
        if algorithm == "AES-256-GCM":
            return self._encrypt_aes_gcm(data, key_data, key_id)
        elif algorithm == "ChaCha20-Poly1305":
            return self._encrypt_chacha20_poly1305(data, key_data, key_id)
        elif algorithm == "Fernet":
            return self._encrypt_fernet(data, key_data, key_id)
        elif algorithm.startswith("RSA"):
            return self._encrypt_rsa(data, key_data, key_id, algorithm)
        else:
            raise ValueError(f"Unsupported encryption algorithm: {algorithm}")
    
    def decrypt_data(self, encrypted_data: EncryptedData) -> bytes:
        """Decrypt data using stored key"""
        key_info = self.key_manager.get_key(encrypted_data.key_id)
        if not key_info:
            raise ValueError(f"Key {encrypted_data.key_id} not found or expired")
        
        key, key_data = key_info
        algorithm = encrypted_data.algorithm
        
        if algorithm == "AES-256-GCM":
            return self._decrypt_aes_gcm(encrypted_data, key_data)
        elif algorithm == "ChaCha20-Poly1305":
            return self._decrypt_chacha20_poly1305(encrypted_data, key_data)
        elif algorithm == "Fernet":
            return self._decrypt_fernet(encrypted_data, key_data)
        elif algorithm.startswith("RSA"):
            return self._decrypt_rsa(encrypted_data, key_data)
        else:
            raise ValueError(f"Unsupported decryption algorithm: {algorithm}")
    
    def _encrypt_aes_gcm(self, data: bytes, key: bytes, key_id: str) -> EncryptedData:
        """Encrypt using AES-256-GCM"""
        iv = secrets.token_bytes(12)  # 96-bit IV for GCM
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        return EncryptedData(
            data=ciphertext,
            key_id=key_id,
            algorithm="AES-256-GCM",
            iv=iv,
            tag=encryptor.tag
        )
    
    def _decrypt_aes_gcm(self, encrypted_data: EncryptedData, key: bytes) -> bytes:
        """Decrypt using AES-256-GCM"""
        cipher = Cipher(algorithms.AES(key), modes.GCM(encrypted_data.iv, encrypted_data.tag))
        decryptor = cipher.decryptor()
        return decryptor.update(encrypted_data.data) + decryptor.finalize()
    
    def _encrypt_chacha20_poly1305(self, data: bytes, key: bytes, key_id: str) -> EncryptedData:
        """Encrypt using ChaCha20-Poly1305"""
        nonce = secrets.token_bytes(12)  # 96-bit nonce
        cipher = Cipher(algorithms.ChaCha20(key, nonce), modes.GCM())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        return EncryptedData(
            data=ciphertext,
            key_id=key_id,
            algorithm="ChaCha20-Poly1305",
            iv=nonce,
            tag=encryptor.tag
        )
    
    def _decrypt_chacha20_poly1305(self, encrypted_data: EncryptedData, key: bytes) -> bytes:
        """Decrypt using ChaCha20-Poly1305"""
        cipher = Cipher(algorithms.ChaCha20(key, encrypted_data.iv), modes.GCM(encrypted_data.tag))
        decryptor = cipher.decryptor()
        return decryptor.update(encrypted_data.data) + decryptor.finalize()
    
    def _encrypt_fernet(self, data: bytes, key: bytes, key_id: str) -> EncryptedData:
        """Encrypt using Fernet"""
        f = Fernet(key)
        ciphertext = f.encrypt(data)
        
        return EncryptedData(
            data=ciphertext,
            key_id=key_id,
            algorithm="Fernet"
        )
    
    def _decrypt_fernet(self, encrypted_data: EncryptedData, key: bytes) -> bytes:
        """Decrypt using Fernet"""
        f = Fernet(key)
        return f.decrypt(encrypted_data.data)
    
    def _encrypt_rsa(self, data: bytes, key: bytes, key_id: str, algorithm: str) -> EncryptedData:
        """Encrypt using RSA"""
        public_key = serialization.load_pem_public_key(key)
        ciphertext = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return EncryptedData(
            data=ciphertext,
            key_id=key_id,
            algorithm=algorithm
        )
    
    def _decrypt_rsa(self, encrypted_data: EncryptedData, key: bytes) -> bytes:
        """Decrypt using RSA"""
        private_key = serialization.load_pem_private_key(key, password=None)
        return private_key.decrypt(
            encrypted_data.data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    async def encrypt_file(self, file_path: str, output_path: Optional[str] = None,
                          key_id: Optional[str] = None) -> str:
        """Encrypt a file"""
        if not HAS_AIOFILES:
            raise ImportError("aiofiles is required for file encryption")
            
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} not found")
        
        output_path = output_path or f"{file_path}.encrypted"
        
        async with aiofiles.open(file_path, 'rb') as f:
            data = await f.read()
        
        encrypted_data = self.encrypt_data(data, key_id)
        
        # Save encrypted data with metadata
        encrypted_file_data = {
            'data': base64.b64encode(encrypted_data.data).decode('utf-8'),
            'key_id': encrypted_data.key_id,
            'algorithm': encrypted_data.algorithm,
            'iv': base64.b64encode(encrypted_data.iv).decode('utf-8') if encrypted_data.iv else None,
            'tag': base64.b64encode(encrypted_data.tag).decode('utf-8') if encrypted_data.tag else None,
            'metadata': encrypted_data.metadata,
            'original_filename': file_path.name,
            'encrypted_at': datetime.utcnow().isoformat()
        }
        
        async with aiofiles.open(output_path, 'w') as f:
            await f.write(json.dumps(encrypted_file_data, indent=2))
        
        logger.info(f"Encrypted file {file_path} to {output_path}")
        return output_path
    
    async def decrypt_file(self, encrypted_file_path: str, output_path: Optional[str] = None) -> str:
        """Decrypt a file"""
        if not HAS_AIOFILES:
            raise ImportError("aiofiles is required for file decryption")
            
        encrypted_file_path = Path(encrypted_file_path)
        if not encrypted_file_path.exists():
            raise FileNotFoundError(f"Encrypted file {encrypted_file_path} not found")
        
        async with aiofiles.open(encrypted_file_path, 'r') as f:
            encrypted_file_data = json.loads(await f.read())
        
        encrypted_data = EncryptedData(
            data=base64.b64decode(encrypted_file_data['data']),
            key_id=encrypted_file_data['key_id'],
            algorithm=encrypted_file_data['algorithm'],
            iv=base64.b64decode(encrypted_file_data['iv']) if encrypted_file_data.get('iv') else None,
            tag=base64.b64decode(encrypted_file_data['tag']) if encrypted_file_data.get('tag') else None,
            metadata=encrypted_file_data.get('metadata', {})
        )
        
        decrypted_data = self.decrypt_data(encrypted_data)
        
        output_path = output_path or encrypted_file_data.get('original_filename', 'decrypted_file')
        
        async with aiofiles.open(output_path, 'wb') as f:
            await f.write(decrypted_data)
        
        logger.info(f"Decrypted file {encrypted_file_path} to {output_path}")
        return output_path
    
    def create_tls_context(self, cert_file: Optional[str] = None, 
                          key_file: Optional[str] = None) -> ssl.SSLContext:
        """Create TLS context for secure communications"""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        
        # Configure for security
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        
        if cert_file and key_file:
            context.load_cert_chain(cert_file, key_file)
        
        return context
    
    def derive_key_from_password(self, password: str, salt: Optional[bytes] = None,
                               algorithm: str = "scrypt") -> Tuple[bytes, bytes]:
        """Derive encryption key from password"""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        if algorithm == "scrypt":
            kdf = Scrypt(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                n=2**14,
                r=8,
                p=1
            )
        elif algorithm == "pbkdf2":
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000
            )
        else:
            raise ValueError(f"Unsupported KDF algorithm: {algorithm}")
        
        key = kdf.derive(password.encode('utf-8'))
        return key, salt
    
    def get_encryption_status(self) -> Dict[str, Any]:
        """Get encryption system status"""
        active_keys = self.key_manager.list_keys(active_only=True)
        
        return {
            'status': 'active',
            'total_keys': len(active_keys),
            'symmetric_keys': len([k for k, v in active_keys.items() if v.key_type == "symmetric"]),
            'asymmetric_keys': len([k for k, v in active_keys.items() if v.key_type.startswith("asymmetric")]),
            'default_algorithm': self.default_algorithm,
            'supported_algorithms': [
                'AES-256-GCM', 'ChaCha20-Poly1305', 'Fernet', 'RSA-2048'
            ]
        }