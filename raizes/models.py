from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from datetime import datetime
from raizes.extensions import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha = Column(String, nullable=False)
    perfil = Column(String, nullable=False, default="CLIENTE")
    consentimento_lgpd = Column(Boolean, nullable=False)
    pontos = Column(Integer, default=0)

class Unidade(Base):
    __tablename__ = "unidades"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    endereco = Column(String, nullable=False)
    is_matriz = Column(Boolean, default=False)

class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    descricao = Column(String, nullable=False)
    preco = Column(Float, nullable=False)
    categoria = Column(String, nullable=False)

class Estoque(Base):
    __tablename__ = "estoques"

    id = Column(Integer, primary_key=True, index=True)
    id_unidade = Column(Integer, ForeignKey("unidades.id"), nullable=False)
    id_produto = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, nullable=False, default=0)

class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    id_cliente = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    id_unidade = Column(Integer, ForeignKey("unidades.id"), nullable=False)
    canal_pedido = Column(String, nullable=False)
    total = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="PREPARO")
    pagamento_mock_payload = Column(String, nullable=True)
    data_criacao = Column(DateTime, default=datetime.utcnow)

class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"

    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    acao = Column(String, nullable=False)
    recurso_id = Column(Integer, nullable=True)
    detalhes = Column(String, nullable=True)
    data_hora = Column(DateTime, default=datetime.utcnow)

class Promocao(Base):
    __tablename__ = "promocoes"
    
    id = Column(Integer, primary_key=True, index=True)
    id_produto = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    id_unidade = Column(Integer, ForeignKey("unidades.id"), nullable=False)
    percentual_desconto = Column(Float, nullable=False)