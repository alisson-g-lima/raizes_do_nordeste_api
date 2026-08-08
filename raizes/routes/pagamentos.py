from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
from raizes.extensions import get_db
from raizes.models import Pedido, Pagamento, LogAuditoria, Usuario
from raizes.schemas import PagamentoRequest, PagamentoResponse
from raizes.security import obter_usuario_atual

router = APIRouter(prefix="/pagamentos", tags=["Pagamentos"])

@router.post("/", response_model=PagamentoResponse, status_code=200)
def processar_pagamento(
    requisicao: PagamentoRequest,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(obter_usuario_atual)
):
    pedido = db.query(Pedido).filter(Pedido.id == requisicao.pedidoId).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    if pedido.status != "PENDENTE":
        raise HTTPException(status_code=409, detail="Pagamento já processado ou pedido não aguarda pagamento.")

    pagamento_atual = db.query(Pagamento).filter(
        Pagamento.pedido_id == pedido.id,
        Pagamento.status == "PENDENTE"
    ).first()

    if not pagamento_atual:
        raise HTTPException(status_code=409, detail="Nenhuma intenção de pagamento pendente localizada.")

    transacao_mock_id = str(uuid.uuid4())
    metodo_informado = requisicao.metodo.upper().strip()
    metodos_permitidos = ["PIX", "DINHEIRO", "CARTAO_DEBITO", "CARTAO_CREDITO"]

    if metodo_informado not in metodos_permitidos:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "PAGAMENTO_RECUSADO",
                "message": "Método de pagamento recusado pelo gateway.",
                "details": [
                    {"field": "metodo", "issue": f"O método '{metodo_informado}' não é aceito pelo sistema."}
                ]
            }
        )

    if metodo_informado == pagamento_atual.metodo:
        pagamento_atual.status = "APROVADO"
        pagamento_atual.payload_gateway = f'{{"transacao": "{transacao_mock_id}", "status": "APROVADO"}}'
        
        pedido.status = "PREPARO"
        
        auditoria = LogAuditoria(
            id_usuario=usuario_logado.id,
            acao="PAGAMENTO_APROVADO",
            recurso_id=pedido.id,
            detalhes=f"Pagamento de R$ {pedido.total:.2f} via {metodo_informado} aprovado. Pedido enviado para cozinha."
        )
        db.add(auditoria)
        db.commit()
        
        return {
            "id": pagamento_atual.id,
            "pedidoId": pedido.id,
            "status": pagamento_atual.status,
            "valor": pedido.total,
            "metodo": pagamento_atual.metodo,
            "transacaoId": transacao_mock_id
        }
        
    else:
        pagamento_atual.status = "RECUSADO"
        pagamento_atual.payload_gateway = f'{{"transacao": "{transacao_mock_id}", "status": "RECUSADO", "motivo": "Divergência de método"}}'
        nova_tentativa_pagamento = Pagamento(
            pedido_id=pedido.id,
            status="PENDENTE",
            metodo=pagamento_atual.metodo
        )
        db.add(nova_tentativa_pagamento)
        
        auditoria = LogAuditoria(
            id_usuario=usuario_logado.id,
            acao="PAGAMENTO_RECUSADO",
            recurso_id=pedido.id,
            detalhes="Tentativa de pagamento recusada. Tente novamente utilizando outra forma de pagamento."
        )
        db.add(auditoria)
        db.commit()
        
        return {
            "id": pagamento_atual.id,
            "pedidoId": pedido.id,
            "status": pagamento_atual.status,
            "valor": pedido.total,
            "metodo": metodo_informado,
            "transacaoId": transacao_mock_id
        }