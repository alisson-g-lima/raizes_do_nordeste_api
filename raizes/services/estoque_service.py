from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from raizes.models import Estoque, Produto, Unidade, LogAuditoria, Usuario
from raizes.schemas import EstoqueUpdate, ProdutoResponse

def listar_estoque_unidade(db: Session, codigo_loja: int, categoria: Optional[str] = None) -> List[ProdutoResponse]:
    loja_ativa = db.query(Unidade).filter(Unidade.id == codigo_loja).first()
    if not loja_ativa:
        raise HTTPException(status_code=404, detail="Tentativa de acesso a uma unidade inexistente.")

    query_estoque = (
        db.query(Produto)
        .join(Estoque, Produto.id == Estoque.id_produto)
        .filter(Estoque.id_unidade == codigo_loja, Estoque.quantidade > 0)
    )
    
    if categoria:
        query_estoque = query_estoque.filter(Produto.categoria == categoria.upper())

    cardapio_disponivel = query_estoque.all()
    
    if not cardapio_disponivel:
        raise HTTPException(status_code=404, detail="Não há itens disponíveis no estoque para os filtros informados.")
        
    return cardapio_disponivel

def carregar_prateleiras(db: Session, lote: EstoqueUpdate, gestor: Usuario) -> dict:
    if gestor.perfil != "GERENTE":
        raise HTTPException(status_code=403, detail="Gestão de estoque restrito à gerência.")
        
    item_cadastrado = db.query(Produto).filter(Produto.id == lote.id_produto).first()
    if not item_cadastrado:
        raise HTTPException(status_code=404, detail="Produto não listado no sistema.")
        
    loja = db.query(Unidade).filter(Unidade.id == lote.id_unidade).first()
    if not loja:
        raise HTTPException(status_code=404, detail="Não conseguimos apontar a loja física para esta carga.")
        
    linha_estoque = db.query(Estoque).filter(
        Estoque.id_produto == lote.id_produto,
        Estoque.id_unidade == lote.id_unidade
    ).first()
    
    if linha_estoque:
        linha_estoque.quantidade += lote.quantidade
    else:
        linha_estoque = Estoque(
            id_produto=lote.id_produto,
            id_unidade=lote.id_unidade,
            quantidade=lote.quantidade
        )
        db.add(linha_estoque)
        
    db.commit()
    db.refresh(linha_estoque)
    
    db.add(LogAuditoria(
        id_usuario=gestor.id, 
        acao="ATUALIZAR_ESTOQUE", 
        recurso_id=linha_estoque.id,
        detalhes=f"Adição de {lote.quantidade} itens ao estoque."
    ))
    db.commit()
    
    return {"mensagem": "Estoque atualizado.", "quantidade_atualizada": linha_estoque.quantidade}