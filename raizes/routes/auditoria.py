from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from raizes.schemas import LogAuditoriaResponse
from raizes.models import LogAuditoria, Usuario
from raizes.extensions import get_db
from raizes.security import obter_usuario_atual

router = APIRouter(prefix="/auditoria", tags=["Auditoria"])

@router.get("/", response_model=List[LogAuditoriaResponse])
def listar_logs_auditoria(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    if usuario.perfil != "GERENTE":
        raise HTTPException(
            status_code=403, 
            detail="Acesso negado. Apenas GERENTES possuem permissão para visualizar a auditoria do sistema."
        )
        
    offset = (page - 1) * limit
    
    logs = db.query(LogAuditoria).order_by(LogAuditoria.data_hora.desc()).offset(offset).limit(limit).all()
    
    if not logs:
        raise HTTPException(
            status_code=404,
            detail="Nenhum registro de auditoria encontrado."
        )
        
    return logs