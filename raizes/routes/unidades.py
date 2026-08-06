from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from raizes.schemas import UnidadeCreate, UnidadeResponse
from raizes.models import Unidade, Usuario, Estoque, LogAuditoria
from raizes.extensions import get_db
from raizes.security import obter_usuario_atual

router = APIRouter(prefix="/unidades", tags=["Unidades"])

@router.get("/", response_model=List[UnidadeResponse])
def mapear_filiais(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    offset = (page - 1) * limit
    filiais = db.query(Unidade).offset(offset).limit(limit).all()
    
    if not filiais:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma unidade de negócio cadastrada ou encontrada no sistema."
        )
        
    return filiais

@router.post("/", response_model=UnidadeResponse, status_code=201)
def inaugurar_loja(
    planta_unidade: UnidadeCreate,
    db: Session = Depends(get_db),
    gestor: Usuario = Depends(obter_usuario_atual)
):
    if gestor.perfil != "GERENTE":
        raise HTTPException(status_code=403, detail="Expansão de rede é restrita ao perfil gerencial.")
        
    if planta_unidade.is_matriz:
        sede_atual = db.query(Unidade).filter(Unidade.is_matriz == True).first()
        if sede_atual:
            raise HTTPException(
                status_code=400, 
                detail="Conflito de infraestrutura: O sistema permite a configuração de apenas uma Matriz."
            )
            
    ponto_fisico = Unidade(**planta_unidade.model_dump()) if hasattr(planta_unidade, 'model_dump') else Unidade(**planta_unidade.dict())
    db.add(ponto_fisico)
    db.commit()
    db.refresh(ponto_fisico)
    
    db.add(LogAuditoria(
        id_usuario=gestor.id, 
        acao="CRIAR_UNIDADE", 
        recurso_id=ponto_fisico.id,
        detalhes=f"Novo ponto comercial registrado no endereço: {ponto_fisico.endereco}"
    ))
    db.commit()
    
    return ponto_fisico

@router.delete("/{codigo_loja}", status_code=200)
def fechar_ponto_comercial(
    codigo_loja: int,
    db: Session = Depends(get_db),
    gestor: Usuario = Depends(obter_usuario_atual)
):
    if gestor.perfil != "GERENTE":
        raise HTTPException(status_code=403, detail="Encerramento de lojas requer login de gerente.")
        
    loja_alvo = db.query(Unidade).filter(Unidade.id == codigo_loja).first()
    if not loja_alvo:
        raise HTTPException(status_code=404, detail="O ID fornecido não bate com nenhuma loja aberta.")
        
    if loja_alvo.is_matriz:
        raise HTTPException(
            status_code=400, 
            detail="Ação perigosa bloqueada: A operação da matriz não pode ser apagada do banco."
        )
        
    db.query(Estoque).filter(Estoque.id_unidade == codigo_loja).delete()
    db.delete(loja_alvo)
    
    db.add(LogAuditoria(
        id_usuario=gestor.id, 
        acao="EXCLUIR_UNIDADE", 
        recurso_id=codigo_loja,
        detalhes="Baixa do ponto comercial efetuada junto com seu histórico de estoque."
    ))
    db.commit()
    
    return {"mensagem": "Operação concluída com sucesso. O ponto comercial foi fechado e os estoques vinculados foram excluídos."}