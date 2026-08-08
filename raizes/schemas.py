from pydantic import BaseModel, validator, root_validator
from typing import List, Optional
from datetime import datetime

class ProdutoCreate(BaseModel):
    nome: str
    descricao: str
    preco: float
    categoria: str

class ProdutoResponse(BaseModel):
    id: int
    nome: str
    descricao: str
    preco: float
    categoria: str
    
    class Config:
        from_attributes = True

class EstoqueUpdate(BaseModel):
    id_produto: int
    id_unidade: int
    quantidade: int

    @validator('quantidade')
    def validar_entrada_estoque(cls, valor):
        if valor <= 0:
            raise ValueError("Não faz sentido adicionar zero ou quantidades negativas no estoque.")
        return valor

class ItemPedidoCreate(BaseModel):
    produto_id: int
    quantidade: int

class ItemPedidoResponse(BaseModel):
    id: int
    produto_id: int
    quantidade: int
    preco_unitario: float

    class Config:
        from_attributes = True

class PedidoCreate(BaseModel):
    id_cliente: int
    id_unidade: int
    canal_pedido: str
    forma_pagamento: str
    itens: List[ItemPedidoCreate]
    resgatar_pontos: Optional[bool] = False

    @validator('canal_pedido')
    def validar_origem_do_pedido(cls, valor):
        canais_permitidos = ['APP', 'TOTEM', 'BALCAO', 'PICKUP']
        valor_formatado = valor.upper().strip()
        if valor_formatado not in canais_permitidos:
            raise ValueError(f"Canal '{valor}' não é reconhecido. Utilize um dos canais oficiais do sistema.")
        return valor_formatado

class PedidoResponse(BaseModel):
    id: int
    canal_pedido: str
    status: str
    total: float
    data_criacao: datetime
    itens: List[ItemPedidoResponse] = []

    class Config:
        from_attributes = True

class PedidoStatusUpdate(BaseModel):
    status: str

class PagamentoRequest(BaseModel):
    pedidoId: int
    metodo: str

class PagamentoResponse(BaseModel):
    id: int
    pedidoId: int
    status: str
    valor: float
    metodo: str
    transacaoId: Optional[str] = None

    class Config:
        from_attributes = True

class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str
    perfil: str = "CLIENTE"
    consentimento_lgpd: bool

    @validator('perfil')
    def classificar_perfil_usuario(cls, valor):
        cargos = ['CLIENTE', 'ATENDENTE', 'GERENTE', 'COZINHA']
        valor_formatado = valor.upper().strip()
        if valor_formatado not in cargos:
            raise ValueError("Cargo inválido para registro no sistema.")
        return valor_formatado

    @validator('consentimento_lgpd')
    def validar_termos_lgpd(cls, valor, values):
        perfil_informado = values.get('perfil', 'CLIENTE').upper()
        if perfil_informado == 'CLIENTE' and not valor:
            raise ValueError("Clientes não podem se cadastrar sem aceitar os termos da LGPD.")
        return valor

class LoginRequest(BaseModel):
    email: str
    senha: str

class UsuarioInfo(BaseModel):
    id: int
    nome: str
    perfil: str
    pontos: Optional[int] = None
    
    @root_validator(skip_on_failure=True)
    def ocultar_pontos_equipe_interna(cls, valores):
        cargo = valores.get('perfil')
        if cargo != 'CLIENTE':
            valores['pontos'] = None
        elif valores.get('pontos') is None:
            valores['pontos'] = 0
        return valores

    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    accessToken: str
    tokenType: str
    usuario: UsuarioInfo

class LogAuditoriaResponse(BaseModel):
    id: int
    id_usuario: int
    acao: str
    recurso_id: Optional[int] = None
    detalhes: Optional[str] = None
    data_hora: datetime

    class Config:
        from_attributes = True

class UnidadeCreate(BaseModel):
    nome: str
    endereco: str
    is_matriz: bool = False

class UnidadeResponse(BaseModel):
    id: int
    nome: str
    endereco: str
    is_matriz: bool

    class Config:
        from_attributes = True

class PromocaoCreate(BaseModel):
    id_produto: int
    id_unidade: int
    percentual_desconto: float

class PromocaoResponse(BaseModel):
    id: int
    id_produto: int
    id_unidade: int
    percentual_desconto: float

    class Config:
        from_attributes = True