from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from raizes.schemas import PromocaoCreate, PromocaoResponse
from raizes.models import Promocao, Usuario, Produto, Unidade, LogAuditoria
from raizes.extensions import get_db
from raizes.security import obter_usuario_atual

router = APIRouter(prefix="/promocoes", tags=["Promoções"])

@router.post("/", response_model=PromocaoResponse, status_code=201)
def habilitar_oferta(
    regras_desconto: PromocaoCreate,
    db: Session = Depends(get_db),
    gestor: Usuario = Depends(obter_usuario_atual)
):
    if gestor.perfil != "GERENTE":
        raise HTTPException(status_code=403, detail="Apenas a gerência aplica cortes de preço.")

    if regras_desconto.percentual_desconto <= 0 or regras_desconto.percentual_desconto > 50:
        raise HTTPException(
            status_code=400, 
            detail="Regra comercial violada: os descontos devem flutuar entre 1% e 50% para evitar prejuízos."
        )

    produto_base = db.query(Produto).filter(Produto.id == regras_desconto.id_produto).first()
    if not produto_base:
        raise HTTPException(status_code=404, detail="Produto alvo da promoção não identificado.")

    loja_base = db.query(Unidade).filter(Unidade.id == regras_desconto.id_unidade).first()
    if not loja_base:
        raise HTTPException(status_code=404, detail="Local da promoção não existe na base.")

    oferta_ativa = db.query(Promocao).filter(
        Promocao.id_produto == regras_desconto.id_produto,
        Promocao.id_unidade == regras_desconto.id_unidade
    ).first()

    if oferta_ativa:
        raise HTTPException(
            status_code=409, 
            detail="Já há uma promoção rodando para essa combinação de produto e loja."
        )

    campanha = Promocao(**regras_desconto.model_dump()) if hasattr(regras_desconto, 'model_dump') else Promocao(**regras_desconto.dict())
    db.add(campanha)
    db.commit()
    db.refresh(campanha)

    db.add(LogAuditoria(
        id_usuario=gestor.id, 
        acao="CRIAR_PROMOCAO", 
        recurso_id=campanha.id,
        detalhes=f"Oferta ativada: {campanha.percentual_desconto}% off."
    ))
    db.commit()

    return campanha

@router.delete("/{codigo_promocao}", status_code=200)
def derrubar_oferta(
    codigo_promocao: int,
    db: Session = Depends(get_db),
    gestor: Usuario = Depends(obter_usuario_atual)
):
    if gestor.perfil != "GERENTE":
        raise HTTPException(status_code=403, detail="Sem privilégios para encerrar campanhas comerciais.")

    oferta = db.query(Promocao).filter(Promocao.id == codigo_promocao).first()
    if not oferta:
        raise HTTPException(status_code=404, detail="Campanha não localizada.")

    db.delete(oferta)

    db.add(LogAuditoria(
        id_usuario=gestor.id, 
        acao="EXCLUIR_PROMOCAO", 
        recurso_id=codigo_promocao,
        detalhes="Oferta revogada pelo painel administrativo."
    ))
    db.commit()
    
    return {"mensagem": "Operação concluída com sucesso. A promoção foi removida."}