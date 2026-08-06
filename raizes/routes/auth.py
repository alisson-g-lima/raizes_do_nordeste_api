from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from raizes.schemas import LoginRequest, LoginResponse, UsuarioInfo, UsuarioCreate
from raizes.models import Usuario
from raizes.extensions import get_db
from raizes.security import (
    verificar_senha, 
    criar_token_jwt, 
    gerar_hash_senha, 
    obter_usuario_atual
)

router = APIRouter(prefix="/auth", tags=["Autenticação"])

@router.post("/cadastro", response_model=UsuarioInfo, status_code=201, response_model_exclude_none=True)
def cadastrar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db)):
    usuario_existente = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado no sistema.")
    
    novo_usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha=gerar_hash_senha(dados.senha),
        perfil=dados.perfil,
        consentimento_lgpd=dados.consentimento_lgpd
    )
    
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    
    return novo_usuario

@router.post("/login", response_model=LoginResponse, response_model_exclude_none=True)
def login(dados: LoginRequest, db: Session = Depends(get_db)):

    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()

    if not usuario or not verificar_senha(dados.senha, usuario.senha):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

    token = criar_token_jwt(usuario.email, usuario.perfil)

    return LoginResponse(
        accessToken=token,
        tokenType="Bearer",
        usuario=UsuarioInfo(
            id=usuario.id,
            nome=usuario.nome,
            perfil=usuario.perfil,
            pontos=usuario.pontos
        )
    )

@router.get("/me", response_model=UsuarioInfo, response_model_exclude_none=True)
def consultar_perfil(usuario: Usuario = Depends(obter_usuario_atual)):
    return usuario