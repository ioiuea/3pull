# Security Crypto

`app/core/security/crypto` は認証用の暗号・ハッシュ機能をまとめるパッケージです。  
FastAPI や `Request` に依存しない utility だけを置きます。

## 何があるか

- `password.py`
  - Argon2id ベースの password hash / verify / rehash 判定
- `token_cipher.py`
  - Entra token の暗号化 / 復号

## 利用方法

### password hash

```python
from app.core.security.crypto import hash_password, needs_rehash, verify_password

password_hash = hash_password(password)
is_valid = verify_password(password, password_hash)
rehash_required = needs_rehash(password_hash)
```

### token encryption

```python
from app.core.security.crypto import decrypt_token, encrypt_token

encrypted = encrypt_token(access_token)
plain = decrypt_token(encrypted)
```

## import ルール

- auth service や repository 補助ロジックから使う
- router から直接 `password.py` や `token_cipher.py` を import しない
- 外部公開は `app.core.security.crypto` から行う

## 置いてはいけないもの

- `Request` `Depends` `HTTPException` を使う logic
- middleware や router 用 dependency
