"""
Security utilities for API key validation and authentication.
"""
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from jose.exceptions import JOSEError
import requests
import json
from .config import settings

# API Key header scheme - expects "X-API-Key" header in requests
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Bearer Token scheme
token_auth_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    api_key_header: str = Security(api_key_header),
    token: HTTPAuthorizationCredentials = Security(token_auth_scheme)
) -> dict:
    """
    Validate authentication using either API Key OR JWT Token.
    
    Priority:
    1. JWT Token (Bearer)
    2. API Key (X-API-Key)
    
    Returns:
        dict: User info or minimal dict for API key
        
    Raises:
        HTTPException: If no valid authentication found
    """
    # 1. Try JWT Validation
    if token:
        try:
            payload = verify_jwt(token.credentials)
            return payload
        except HTTPException as e:
            # If token is present but invalid, raise the error immediately
            # Don't fall back to API key if a token was attempted but failed
            raise e
        except Exception as e:
            pass # Fallthrough if token format is weird (unlikely with HTTPBearer)

    # 2. Try API Key Validation
    if api_key_header:
        # POC: Simple validation against secret key
        if api_key_header == settings.API_KEY_SECRET:
            return {"sub": "internal_extension", "scope": "admin"}
    
    # 3. No valid auth found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_jwt(token: str) -> dict:
    """
    Verify the JWT token from Auth0.
    """
    domain = settings.AUTH0_DOMAIN
    audience = settings.AUTH0_AUDIENCE
    algorithms = settings.AUTH0_ALGORITHMS

    try:
        # Get JWKS from Auth0
        jwks_url = f"https://{domain}/.well-known/jwks.json"
        jwks_client = requests.get(jwks_url)
        jwks = jwks_client.json()

        # Get header from token
        unverified_header = jwt.get_unverified_header(token)
        
        # Determine which key was used to sign the token
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
        
        if rsa_key:
            try:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=algorithms,
                    audience=audience,
                    issuer=f"https://{domain}/"
                )
                return payload

            except jwt.ExpiredSignatureError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token is expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except jwt.JWTClaimsError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect claims, check audience and issuer.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to parse authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
                
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find appropriate key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except JOSEError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
