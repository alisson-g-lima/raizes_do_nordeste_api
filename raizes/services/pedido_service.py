from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from raizes.models import Pedido, Estoque, Produto, Usuario, LogAuditoria, Promocao, Unidade, Pagamento, ItemPedido
from raizes.schemas import PedidoCreate

def criar_pedido_com_pagamento(db: Session, dados_requisicao: PedidoCreate) -> Pedido:
    unidade_db = db.query(Unidade).filter(Unidade.id == dados_requisicao.id_unidade).first()
    if not unidade_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"A unidade com ID {dados_requisicao.id_unidade} não foi encontrada no sistema."
        )

    total_da_compra = 0.0
    lista_itens = []

    for item_carrinho in dados_requisicao.itens:
        produto_db = db.query(Produto).filter(Produto.id == item_carrinho.produto_id).first()
        if not produto_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Não encontramos nenhum produto com o ID {item_carrinho.produto_id}."
            )

        registro_estoque = db.query(Estoque).filter(
            Estoque.id_unidade == dados_requisicao.id_unidade,
            Estoque.id_produto == item_carrinho.produto_id
        ).first()

        if not registro_estoque or registro_estoque.quantidade < item_carrinho.quantidade:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=f"Falta de estoque: não temos a quantidade solicitada de '{produto_db.nome}'."
            )

        desconto_ativo = db.query(Promocao).filter(
            Promocao.id_produto == item_carrinho.produto_id,
            Promocao.id_unidade == dados_requisicao.id_unidade
        ).first()
        
        valor_base = produto_db.preco
        if desconto_ativo:
            abatimento = valor_base * (desconto_ativo.percentual_desconto / 100.0)
            valor_base -= abatimento

        total_da_compra += (valor_base * item_carrinho.quantidade)
        registro_estoque.quantidade -= item_carrinho.quantidade
        
        lista_itens.append(
            ItemPedido(
                produto_id=item_carrinho.produto_id,
                quantidade=item_carrinho.quantidade,
                preco_unitario=valor_base
            )
        )

    comprador = db.query(Usuario).filter(Usuario.id == dados_requisicao.id_cliente).first()
    
    if comprador and comprador.perfil == "CLIENTE" and dados_requisicao.resgatar_pontos:
        if comprador.pontos > 0:
            valor_desconto_pontos = comprador.pontos / 10.0
            
            if valor_desconto_pontos >= total_da_compra:
                moedas_gastas = int(total_da_compra * 10)
                comprador.pontos -= moedas_gastas
                total_da_compra = 0.0
            else:
                total_da_compra -= valor_desconto_pontos
                comprador.pontos = 0

    metodos_liberados = ["PIX", "CARTAO_CREDITO", "CARTAO_DEBITO", "DINHEIRO"]
    pagamento_escolhido = dados_requisicao.forma_pagamento.upper().strip()

    if pagamento_escolhido not in metodos_liberados:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Método {pagamento_escolhido} rejeitado. Aceitamos apenas Pix, Cartões ou Dinheiro."
        )

    pedido_fechado = Pedido(
        id_cliente=dados_requisicao.id_cliente,
        id_unidade=dados_requisicao.id_unidade,
        canal_pedido=dados_requisicao.canal_pedido,
        total=total_da_compra,
        status="PENDENTE",
        itens=lista_itens
    )
    
    db.add(pedido_fechado)
    db.flush()

    registro_pagamento = Pagamento(
        pedido_id=pedido_fechado.id,
        status="PENDENTE",
        metodo=pagamento_escolhido
    )
    db.add(registro_pagamento)

    if comprador and comprador.perfil == "CLIENTE" and total_da_compra > 0:
        comprador.pontos += int(total_da_compra)

    db.commit()
    db.refresh(pedido_fechado)
    
    log_venda = LogAuditoria(
        id_usuario=dados_requisicao.id_cliente,
        acao="CRIAR_PEDIDO",
        recurso_id=pedido_fechado.id,
        detalhes=f"Pedido registrado via {dados_requisicao.canal_pedido}. Aguardando pagamento de R$ {total_da_compra:.2f}"
    )
    db.add(log_venda)
    db.commit()
    
    return pedido_fechado