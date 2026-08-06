from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from raizes.schemas import ProdutoCreate, ProdutoResponse
from raizes.models import Produto, Usuario, LogAuditoria, Estoque, Promocao
from raizes.extensions import get_db
from raizes.security import obter_usuario_atual

router = APIRouter(prefix="/produtos", tags=["Cardápio"])

@router.post("/", response_model=ProdutoResponse, status_code=201)
def catalogar_item(
    item: ProdutoCreate,
    db: Session = Depends(get_db),
    gestor: Usuario = Depends(obter_usuario_atual)
):
    if gestor.perfil != "GERENTE":
        raise HTTPException(status_code=403, detail="Apenas gerentes podem alterar o cardápio.")
        
    novo_produto = Produto(**item.model_dump()) if hasattr(item, 'model_dump') else Produto(**item.dict())
    db.add(novo_produto)
    db.commit()
    db.refresh(novo_produto)
    
    db.add(LogAuditoria(
        id_usuario=gestor.id, 
        acao="CRIAR_PRODUTO", 
        recurso_id=novo_produto.id,
        detalhes=f"Novo item adicionado ao cardápio: {novo_produto.nome}"
    ))
    db.commit()
    
    return novo_produto

@router.delete("/{codigo_item}", status_code=200)
def remover_do_cardapio(
    codigo_item: int,
    db: Session = Depends(get_db),
    gestor: Usuario = Depends(obter_usuario_atual)
):
    if gestor.perfil != "GERENTE":
        raise HTTPException(status_code=403, detail="Apenas gerentes podem remover itens do cardápio.")
        
    produto_alvo = db.query(Produto).filter(Produto.id == codigo_item).first()
    if not produto_alvo:
        raise HTTPException(status_code=404, detail="Produto não encontrado no sistema.")
        
    db.query(Estoque).filter(Estoque.id_produto == codigo_item).delete()
    db.query(Promocao).filter(Promocao.id_produto == codigo_item).delete()
    
    db.delete(produto_alvo)
    
    db.add(LogAuditoria(
        id_usuario=gestor.id, 
        acao="EXCLUIR_PRODUTO", 
        recurso_id=codigo_item,
        detalhes="Item removido do cardápio permanentemente."
    ))
    db.commit()
    
    return {"mensagem": "Operação concluída com sucesso. O item foi removido do cardápio."}