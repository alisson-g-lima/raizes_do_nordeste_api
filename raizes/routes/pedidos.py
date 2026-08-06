from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from raizes.schemas import PedidoCreate, PedidoResponse
from raizes.models import Pedido, Usuario, LogAuditoria
from raizes.extensions import get_db
from raizes.services import pedido_service
from raizes.security import obter_usuario_atual

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])

@router.get("/", response_model=List[PedidoResponse])
def listar_pedidos(
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(obter_usuario_atual),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    canalPedido: Optional[str] = Query(None)
):
    base_query = db.query(Pedido)

    if usuario_logado.perfil == "CLIENTE":
        base_query = base_query.filter(Pedido.id_cliente == usuario_logado.id)
        
    if canalPedido:
        base_query = base_query.filter(Pedido.canal_pedido == canalPedido.upper())
        
    pulo = (page - 1) * limit
    pedidos_encontrados = base_query.offset(pulo).limit(limit).all()
    
    if not pedidos_encontrados:
        contexto = f" filtrado pelo canal {canalPedido}" if canalPedido else ""
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum pedido encontrado{contexto}."
        )
        
    return pedidos_encontrados

@router.get("/{id_loja_fisica}", response_model=List[PedidoResponse])
def listar_pedidos_por_unidade(
    id_loja_fisica: int,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(obter_usuario_atual),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    pedidos_loja = db.query(Pedido).filter(Pedido.id_unidade == id_loja_fisica)

    if usuario_logado.perfil == "CLIENTE":
        pedidos_loja = pedidos_loja.filter(Pedido.id_cliente == usuario_logado.id)
        
    pulo = (page - 1) * limit
    pedidos_encontrados = pedidos_loja.offset(pulo).limit(limit).all()
    
    if not pedidos_encontrados:
        raise HTTPException(
            status_code=404,
            detail=f"Não localizamos nenhuma movimentação de pedido atrelada à unidade {id_loja_fisica}."
        )
        
    return pedidos_encontrados

@router.post("/", response_model=PedidoResponse, status_code=201)
def lancar_novo_pedido(
    dados_compra: PedidoCreate, 
    db: Session = Depends(get_db),
    cliente_ou_atendente: Usuario = Depends(obter_usuario_atual)
):
    cargo = cliente_ou_atendente.perfil
    
    try:
        if cargo not in ["CLIENTE", "ATENDENTE"]:
            raise HTTPException(
                status_code=403, 
                detail="Apenas clientes finais ou caixas da loja podem emitir pedidos."
            )

        if cargo == "CLIENTE" and dados_compra.id_cliente != cliente_ou_atendente.id:
            raise HTTPException(
                status_code=403, 
                detail="Falha de integridade: a conta autenticada não corresponde ao titular da compra."
            )

        if cargo == "ATENDENTE":
            cliente_alvo = db.query(Usuario).filter(Usuario.id == dados_compra.id_cliente).first()
            if not cliente_alvo or cliente_alvo.perfil != "CLIENTE":
                raise HTTPException(
                    status_code=403,
                    detail="O atendente só pode registrar pedidos para contas com perfil de CLIENTE."
                )

        if dados_compra.canal_pedido == "BALCAO" and cargo != "ATENDENTE":
            raise HTTPException(
                status_code=403, 
                detail="Você está tentando abrir um pedido presencial via plataforma online."
            )

        if cargo == "ATENDENTE" and dados_compra.canal_pedido in ["APP", "TOTEM", "PICKUP"]:
            raise HTTPException(
                status_code=403, 
                detail="Atendentes só podem registrar vendas na modalidade BALCAO."
            )

        return pedido_service.criar_pedido_com_pagamento(db, dados_compra)

    except HTTPException:
        raise
    except Exception as erro_generico:
        raise HTTPException(status_code=400, detail=str(erro_generico))

@router.patch("/{id_alvo}/pronto", response_model=PedidoResponse)
def liberar_pedido_cozinha(
    id_alvo: int, 
    db: Session = Depends(get_db),
    chapeiro_cozinheiro: Usuario = Depends(obter_usuario_atual)
):
    if chapeiro_cozinheiro.perfil != "COZINHA":
        raise HTTPException(
            status_code=403, 
            detail="Ação restrita à equipe de cozinha."
        )
        
    comanda = db.query(Pedido).filter(Pedido.id == id_alvo).first()
    if not comanda:
        raise HTTPException(status_code=404, detail="Comanda não localizada no sistema ativo.")
        
    comanda.status = "PRONTO"
    db.commit()
    db.refresh(comanda)
    
    auditoria = LogAuditoria(
        id_usuario=chapeiro_cozinheiro.id,
        acao="ATUALIZAR_STATUS",
        recurso_id=comanda.id,
        detalhes="O pedido foi concluído na chapa/cozinha."
    )
    db.add(auditoria)
    db.commit()
    
    return comanda

@router.patch("/{id_alvo}/entregue", response_model=PedidoResponse)
def finalizar_entrega_balcao(
    id_alvo: int,
    db: Session = Depends(get_db),
    atendente: Usuario = Depends(obter_usuario_atual)
):
    if atendente.perfil != "ATENDENTE":
        raise HTTPException(
            status_code=403, 
            detail="Apenas quem atende o público pode dar baixa na entrega."
        )
        
    comanda = db.query(Pedido).filter(Pedido.id == id_alvo).first()
    if not comanda:
        raise HTTPException(status_code=404, detail="Pedido inexistente.")
        
    if comanda.status != "PRONTO":
        raise HTTPException(
            status_code=400, 
            detail="O prato ainda não saiu da cozinha. Aguarde a finalização."
        )
        
    comanda.status = "ENTREGUE"
    db.commit()
    db.refresh(comanda)
    
    auditoria = LogAuditoria(
        id_usuario=atendente.id,
        acao="ATUALIZAR_STATUS",
        recurso_id=comanda.id,
        detalhes="Cliente recebeu o pacote no balcão."
    )
    db.add(auditoria)
    db.commit()
    
    return comanda

@router.patch("/{id_alvo}/cancelar", response_model=PedidoResponse)
def forcar_cancelamento(
    id_alvo: int,
    db: Session = Depends(get_db),
    supervisor: Usuario = Depends(obter_usuario_atual)
):
    if supervisor.perfil not in ["ATENDENTE", "GERENTE"]:
        raise HTTPException(
            status_code=403, 
            detail="Apenas níveis de gerência ou caixa podem estornar pagamentos."
        )
        
    comanda = db.query(Pedido).filter(Pedido.id == id_alvo).first()
    if not comanda:
        raise HTTPException(status_code=404, detail="O pedido solicitado para cancelamento não existe.")
        
    if comanda.status in ["ENTREGUE", "CANCELADO"]:
        raise HTTPException(
            status_code=400, 
            detail="Bloqueio de segurança: este pedido já teve seu ciclo de vida encerrado."
        )
        
    comanda.status = "CANCELADO"
    db.commit()
    db.refresh(comanda)
    
    auditoria = LogAuditoria(
        id_usuario=supervisor.id,
        acao="CANCELAR_PEDIDO",
        recurso_id=comanda.id,
        detalhes=f"Estorno forçado por {supervisor.perfil}."
    )
    db.add(auditoria)
    db.commit()
    
    return comanda