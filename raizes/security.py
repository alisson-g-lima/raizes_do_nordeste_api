import hashlib
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from raizes.extensions import get_db
from raizes.models import Usuario

SECRET_KEY = "chaveSecreta"
ALGORITHM = "HS256"

esquema_seguranca = HTTPBearer()

def gerar_hash_senha(senha_texto: str) -> str:
    return hashlib.sha256(senha_texto.encode()).hexdigest()

def verificar_senha(senha_digitada: str, senha_banco: str) -> bool:
    return gerar_hash_senha(senha_digitada) == senha_banco

def criar_token_jwt(email: str, perfil_usuario: str):
    limite_tempo = datetime.utcnow() + timedelta(hours=2)
    carga = {
        "sub": email,
        "perfil": perfil_usuario,
        "exp": limite_tempo
    }
    return jwt.encode(carga, SECRET_KEY, algorithm=ALGORITHM)

def decodificar_token(credenciais: HTTPAuthorizationCredentials = Security(esquema_seguranca)):
    try:
        chave_token = credenciais.credentials
        return jwt.decode(chave_token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sua sessão expirou. Faça login novamente.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token de autenticação corrompido ou inválido.")

def obter_usuario_atual(payload: dict = Depends(decodificar_token), db: Session = Depends(get_db)) -> Usuario:
    if not payload or not isinstance(payload, dict):
        raise HTTPException(status_code=401, detail="Estrutura do token irreconhecível.")
    
    email_registrado = payload.get("sub") or payload.get("email")
    if not email_registrado:
        raise HTTPException(status_code=401, detail="Identificação do usuário ausente no token.")
        
    usuario_banco = db.query(Usuario).filter(Usuario.email == email_registrado).first()
    if not usuario_banco:
        raise HTTPException(status_code=401, detail="Esta conta não existe mais no nosso banco de dados.")
        
    return usuario_banco