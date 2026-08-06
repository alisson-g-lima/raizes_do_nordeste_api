from raizes.extensions import SessionLocal, engine, Base
from raizes.models import Usuario, Unidade, Produto, Estoque

def inicializar_estrutura_banco():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Unidade).first():
        print("[!] Ignorando seed: A infraestrutura do banco 'raizes.db' já foi montada anteriormente.")
        db.close()
        return

    print(">> Zerando registros antigos e preparando o terreno para a nova carga de dados...")

    db.query(Estoque).delete()
    db.query(Produto).delete()
    db.query(Unidade).delete()
    db.query(Usuario).delete()
    db.commit()

    print(">> Subindo filiais na rede...")
    sede = Unidade(nome="Matriz Recife", endereco="Boa Viagem, Recife-PE", is_matriz=True)
    franquia_olinda = Unidade(nome="Filial Olinda", endereco="Centro Histórico, Olinda-PE", is_matriz=False)
    franquia_caruaru = Unidade(nome="Filial Caruaru", endereco="Alto do Moura, Caruaru-PE", is_matriz=False)
    
    db.add_all([sede, franquia_olinda, franquia_caruaru])
    db.commit()

    print(">> Cadastrando pratos e bebidas regionais...")
    pratos_bebidas = [
        Produto(nome="Cuscuz Recheado", descricao="Com charque e queijo coalho", preco=18.50, categoria="PRATO"),
        Produto(nome="Tapioca de Carne de Sol", descricao="Manteiga de garrafa e queijo", preco=22.00, categoria="PRATO"),
        Produto(nome="Bolo de Macaxeira", descricao="Fatia tradicional nordestina", preco=12.00, categoria="PRATO"),
        Produto(nome="Baião de Dois", descricao="Arroz, feijão de corda, carne seca e queijo", preco=35.00, categoria="PRATO"),
        Produto(nome="Escondidinho de Charque", descricao="Purê de macaxeira com charque", preco=28.90, categoria="PRATO"),
        Produto(nome="Moqueca Pernambucana", descricao="Peixe com leite de coco e azeite de dendê", preco=45.00, categoria="PRATO"),
        Produto(nome="Bolo de Rolo", descricao="Sobremesa clássica com goiabada", preco=15.00, categoria="PRATO"),
        Produto(nome="Suco de Cajá", descricao="Copo 400ml", preco=8.00, categoria="BEBIDA"),
        Produto(nome="Suco de Umbu", descricao="Copo 400ml", preco=8.00, categoria="BEBIDA"),
        Produto(nome="Cajuína", descricao="Garrafa 500ml", preco=10.00, categoria="BEBIDA"),
    ]
    db.add_all(pratos_bebidas)
    db.commit()

    print(">> Reabastecendo estoques nas geladeiras locais...")
    lotes_estoque = []
    
    for item in pratos_bebidas:
        lotes_estoque.append(Estoque(id_unidade=sede.id, id_produto=item.id, quantidade=50))
        
    menu_olinda = [p for p in pratos_bebidas if p.nome not in ["Moqueca Pernambucana", "Baião de Dois", "Suco de Umbu"]]
    for item in menu_olinda:
        lotes_estoque.append(Estoque(id_unidade=franquia_olinda.id, id_produto=item.id, quantidade=20))

    menu_caruaru = [p for p in pratos_bebidas if p.nome not in ["Bolo de Rolo", "Cajuína"]]
    for item in menu_caruaru:
        lotes_estoque.append(Estoque(id_unidade=franquia_caruaru.id, id_produto=item.id, quantidade=30))

    db.add_all(lotes_estoque)
    db.commit()
    db.close()
    
    print(">> Sucesso! O setup do ambiente de simulação Raízes do Nordeste foi concluído.")

if __name__ == "__main__":
    inicializar_estrutura_banco()