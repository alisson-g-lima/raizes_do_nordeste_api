from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from raizes.schemas import EstoqueUpdate, ProdutoResponse
from raizes.models import Usuario
from raizes.extensions import get_db
from raizes.security import obter_usuario_atual
from raizes.services import estoque_service

router = APIRouter(prefix="/estoque", tags=["Estoque"])

@router.get("/unidade/{codigo_loja}", response_model=List[ProdutoResponse])
def consultar_estoque_loja(
    codigo_loja: int,
    db: Session = Depends(get_db), 
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    categoria: Optional[str] = Query(None, description="Filtrar por categoria (ex: PRATO, BEBIDA) - Query Param")
):
    return estoque_service.listar_estoque_unidade(db, codigo_loja, categoria)

@router.post("/", status_code=200)
def gerenciar_carga_estoque(
    lote: EstoqueUpdate,
    db: Session = Depends(get_db),
    gestor: Usuario = Depends(obter_usuario_atual)
):
    return estoque_service.carregar_prateleiras(db, lote, gestor)