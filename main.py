from datetime import datetime, date
from enum import Enum
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from pydantic_settings import BaseSettings
from sqlalchemy import (
    create_engine, String, Integer, Float, DateTime, Enum as SAEnum,
    ForeignKey, Boolean, Date, func
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Mapped, mapped_column, Session



# =========================
# Config & DB
# =========================
class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./app.db"
    API_KEYS: list[str] = ["dev-123"]  # troque/adicione aqui ou use variável de ambiente

settings = Settings()
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Auth simples via header x-api-key
def require_api_key(x_api_key: str = Header(..., alias="x-api-key")):
    if x_api_key not in settings.API_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key inválida")
    return True

# =========================
# Models (SQLAlchemy)
# =========================
class OrderStatus(str, Enum):
    RASCUNHO = "rascunho"
    PENDENTE_APROVACAO = "pendente_aprovacao"
    REPROVADO = "reprovado"
    APROVADO = "aprovado"
    AUTORIZADO = "autorizado"  # aprovado e pronto pra receber
    RECEBIDO = "recebido"

class Unidade(Base):
    __tablename__ = "unidades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String, unique=True, index=True)
    nome: Mapped[str] = mapped_column(String)
    cnpj: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    centro_custo: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)

class Fornecedor(Base):
    __tablename__ = "fornecedores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String, unique=True, index=True)
    razao_social: Mapped[str] = mapped_column(String)
    cnpj: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email_pedidos: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sla_dias: Mapped[int] = mapped_column(Integer, default=2)

class Produto(Base):
    __tablename__ = "produtos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String, unique=True, index=True)
    nome: Mapped[str] = mapped_column(String)
    unidade_medida: Mapped[str] = mapped_column(String, default="UN")
    fornecedor_id: Mapped[int] = mapped_column(ForeignKey("fornecedores.id"))
    preco: Mapped[float] = mapped_column(Float, default=0.0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    fornecedor: Mapped[Fornecedor] = relationship("Fornecedor")

class Limite(Base):
    __tablename__ = "limites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"))
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"))
    minimo: Mapped[float] = mapped_column(Float, default=0.0)
    maximo: Mapped[float] = mapped_column(Float, default=999999.0)
    unidade: Mapped[Unidade] = relationship("Unidade")
    produto: Mapped[Produto] = relationship("Produto")

class Pedido(Base):
    __tablename__ = "pedidos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"))
    gerente_nome: Mapped[str] = mapped_column(String)
    contato: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    fornecedor_id: Mapped[int] = mapped_column(ForeignKey("fornecedores.id"))
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), default=OrderStatus.RASCUNHO)
    desejado_para: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    valor_total: Mapped[float] = mapped_column(Float, default=0.0)

    unidade: Mapped[Unidade] = relationship("Unidade")
    fornecedor: Mapped[Fornecedor] = relationship("Fornecedor")
    itens: Mapped[List["ItemPedido"]] = relationship("ItemPedido", cascade="all, delete-orphan", back_populates="pedido")
    aprovacoes: Mapped[List["Aprovacao"]] = relationship("Aprovacao", cascade="all, delete-orphan", back_populates="pedido")
    recebimentos: Mapped[List["Recebimento"]] = relationship("Recebimento", cascade="all, delete-orphan", back_populates="pedido")

class ItemPedido(Base):
    __tablename__ = "itens_pedido"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"))
    quantidade: Mapped[float] = mapped_column(Float)
    preco: Mapped[float] = mapped_column(Float)
    subtotal: Mapped[float] = mapped_column(Float)
    motivo: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    pedido: Mapped[Pedido] = relationship("Pedido", back_populates="itens")
    produto: Mapped[Produto] = relationship("Produto")

class Aprovacao(Base):
    __tablename__ = "aprovacoes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    decisor: Mapped[str] = mapped_column(String)
    aprovado: Mapped[bool] = mapped_column(Boolean)
    motivo: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    carimbo: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    pedido: Mapped[Pedido] = relationship("Pedido", back_populates="aprovacoes")

class Recebimento(Base):
    __tablename__ = "recebimentos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    data_recebimento: Mapped[date] = mapped_column(Date)
    quantidade_recebida: Mapped[float] = mapped_column(Float)
    divergencia: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pedido: Mapped[Pedido] = relationship("Pedido", back_populates="recebimentos")

Base.metadata.create_all(engine)

# =========================
# Schemas (Pydantic)
# =========================
class UnidadeIn(BaseModel):
    codigo: str
    nome: str
    cnpj: Optional[str] = None
    centro_custo: Optional[str] = None
    ativa: bool = True

class UnidadeOut(UnidadeIn):
    id: int
    model_config = ConfigDict(from_attributes=True)

class FornecedorIn(BaseModel):
    codigo: str
    razao_social: str
    cnpj: Optional[str] = None
    email_pedidos: Optional[str] = None
    sla_dias: int = 2

class FornecedorOut(FornecedorIn):
    id: int
    model_config = ConfigDict(from_attributes=True)

class ProdutoIn(BaseModel):
    codigo: str
    nome: str
    unidade_medida: str = "UN"
    fornecedor_id: int
    preco: float = 0.0
    ativo: bool = True

class ProdutoOut(ProdutoIn):
    id: int
    model_config = ConfigDict(from_attributes=True)

class LimiteIn(BaseModel):
    unidade_id: int
    produto_id: int
    minimo: float = 0.0
    maximo: float = 999999.0

class LimiteOut(LimiteIn):
    id: int
    model_config = ConfigDict(from_attributes=True)

class ItemIn(BaseModel):
    produto_id: int
    quantidade: float = Field(gt=0)
    preco: Optional[float] = None
    motivo: Optional[str] = None

class ItemOut(BaseModel):
    id: int
    produto_id: int
    quantidade: float
    preco: float
    subtotal: float
    motivo: Optional[str]
    model_config = ConfigDict(from_attributes=True)

class PedidoIn(BaseModel):
    unidade_id: int
    gerente_nome: str
    contato: Optional[str] = None
    fornecedor_id: int
    desejado_para: Optional[date] = None
    observacoes: Optional[str] = None
    itens: List[ItemIn]

class PedidoOut(BaseModel):
    id: int
    criado_em: datetime
    unidade_id: int
    fornecedor_id: int
    gerente_nome: str
    contato: Optional[str]
    status: OrderStatus
    desejado_para: Optional[date]
    observacoes: Optional[str]
    valor_total: float
    itens: List[ItemOut]
    model_config = ConfigDict(from_attributes=True)

class AprovarIn(BaseModel):
    decisor: str
    aprovado: bool
    motivo: Optional[str] = None

class RecebimentoIn(BaseModel):
    data_recebimento: date
    quantidade_recebida: float = Field(gt=0)
    divergencia: Optional[str] = None

# =========================
# Helpers de negócios
# =========================
def calcular_total(pedido: Pedido):
    total = 0.0
    for it in pedido.itens:
        total += it.subtotal
    pedido.valor_total = round(total, 2)

def validar_limites(db: Session, pedido: Pedido) -> bool:
    precisa_aprovacao = False
    for it in pedido.itens:
        lim = db.query(Limite).filter(
            Limite.unidade_id == pedido.unidade_id,
            Limite.produto_id == it.produto_id
        ).one_or_none()
        if lim:
            if it.quantidade < lim.minimo or it.quantidade > lim.maximo:
                precisa_aprovacao = True
    return precisa_aprovacao

# =========================
# App & Rotas
# =========================
app = FastAPI(
    title="MaisQueCafe API",
    version="0.2.0",
    description="Mini-ERP de pedidos para lojas de cafeteria. Use x-api-key em todas as requisições."
)

# CORS: ajuste allow_origins para o domínio do seu painel quando publicar
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/status", tags=["Util"])
def status_ok():
    return {"ok": True, "time": datetime.utcnow().isoformat()}

# --------- CADASTROS ---------
@app.post("/unidades", response_model=UnidadeOut, dependencies=[Depends(require_api_key)], tags=["Cadastros"])
def create_unidade(payload: UnidadeIn, db: Session = Depends(get_db)):
    u = Unidade(**payload.model_dump())
    db.add(u); db.commit(); db.refresh(u); return u

@app.get("/unidades", response_model=List[UnidadeOut], dependencies=[Depends(require_api_key)], tags=["Cadastros"])
def list_unidades(db: Session = Depends(get_db)):
    return db.query(Unidade).all()

@app.delete("/unidades/{unidade_id}", dependencies=[Depends(require_api_key)], tags=["Cadastros"])
def delete_unidade(unidade_id: int, db: Session = Depends(get_db)):
    u = db.get(Unidade, unidade_id)
    if not u:
        raise HTTPException(404, "Unidade não encontrada")
    # checa dependências
    has_pedidos = db.query(Pedido).filter(Pedido.unidade_id == unidade_id).first()
    if has_pedidos:
        raise HTTPException(400, "Unidade possui pedidos vinculados")
    db.delete(u); db.commit()
    return {"ok": True}

@app.post("/fornecedores", response_model=FornecedorOut, dependencies=[Depends(require_api_key)], tags=["Cadastros"])
def create_fornecedor(payload: FornecedorIn, db: Session = Depends(get_db)):
    f = Fornecedor(**payload.model_dump())
    db.add(f); db.commit(); db.refresh(f); return f

@app.get("/fornecedores", response_model=List[FornecedorOut], dependencies=[Depends(require_api_key)], tags=["Cadastros"])
def list_fornecedores(db: Session = Depends(get_db)):
    return db.query(Fornecedor).all()

@app.delete("/fornecedores/{fornecedor_id}", dependencies=[Depends(require_api_key)], tags=["Cadastros"])
def delete_fornecedor(fornecedor_id: int, db: Session = Depends(get_db)):
    f = db.get(Fornecedor, fornecedor_id)
    if not f:
        raise HTTPException(404, "Fornecedor não encontrado")
    has_prod = db.query(Produto).filter(Produto.fornecedor_id == fornecedor_id).first()
    if has_prod:
        raise HTTPException(400, "Fornecedor possui produtos vinculados")
    db.delete(f); db.commit()
    return {"ok": True}

@app.post("/produtos", response_model=ProdutoOut, dependencies=[Depends(require_api_key)], tags=["Cadastros"])
def create_produto(payload: ProdutoIn, db: Session = Depends(get_db)):
    if not db.get(Fornecedor, payload.fornecedor_id):
        raise HTTPException(400, "Fornecedor inválido")
    p = Produto(**payload.model_dump())
    db.add(p); db.commit(); db.refresh(p); return p

@app.get("/produtos", response_model=List[ProdutoOut], dependencies=[Depends(require_api_key)], tags=["Cadastros"])
def list_produtos(ativo: Optional[bool] = None, fornecedor_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Produto)
    if ativo is not None: q = q.filter(Produto.ativo == ativo)
    if fornecedor_id is not None: q = q.filter(Produto.fornecedor_id == fornecedor_id)
    return q.all()

@app.delete("/produtos/{produto_id}", dependencies=[Depends(require_api_key)], tags=["Cadastros"])
def delete_produto(produto_id: int, db: Session = Depends(get_db)):
    p = db.get(Produto, produto_id)
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    has_lim = db.query(Limite).filter(Limite.produto_id == produto_id).first()
    if has_lim:
        raise HTTPException(400, "Produto possui limites vinculados")
    has_item = db.query(ItemPedido).filter(ItemPedido.produto_id == produto_id).first()
    if has_item:
        raise HTTPException(400, "Produto possui itens de pedido")
    db.delete(p); db.commit()
    return {"ok": True}

@app.post("/limites", response_model=LimiteOut, dependencies=[Depends(require_api_key)], tags=["Cadastros"])
def create_limite(payload: LimiteIn, db: Session = Depends(get_db)):
    if not db.get(Unidade, payload.unidade_id): raise HTTPException(400, "Unidade inválida")
    if not db.get(Produto, payload.produto_id): raise HTTPException(400, "Produto inválido")
    l = Limite(**payload.model_dump())
    db.add(l); db.commit(); db.refresh(l); return l

@app.get("/limites", response_model=List[LimiteOut], dependencies=[Depends(require_api_key)], tags=["Cadastros"])
def list_limites(db: Session = Depends(get_db)):
    return db.query(Limite).all()

@app.delete("/limites/{limite_id}", dependencies=[Depends(require_api_key)], tags=["Cadastros"])
def delete_limite(limite_id: int, db: Session = Depends(get_db)):
    l = db.get(Limite, limite_id)
    if not l:
        raise HTTPException(404, "Limite não encontrado")
    db.delete(l); db.commit()
    return {"ok": True}

# --------- PEDIDOS ---------
@app.post("/pedidos", response_model=PedidoOut, dependencies=[Depends(require_api_key)], tags=["Pedidos"])
def criar_pedido(payload: PedidoIn, db: Session = Depends(get_db)):
    if not db.get(Unidade, payload.unidade_id): raise HTTPException(400, "Unidade inválida")
    if not db.get(Fornecedor, payload.fornecedor_id): raise HTTPException(400, "Fornecedor inválido")

    pedido = Pedido(
        unidade_id=payload.unidade_id,
        gerente_nome=payload.gerente_nome,
        contato=payload.contato,
        fornecedor_id=payload.fornecedor_id,
        desejado_para=payload.desejado_para,
        observacoes=payload.observacoes,
        status=OrderStatus.RASCUNHO
    )
    db.add(pedido); db.flush()

    itens: list[ItemPedido] = []
    for item in payload.itens:
        prod = db.get(Produto, item.produto_id)
        if not prod or not prod.ativo or prod.fornecedor_id != payload.fornecedor_id:
            raise HTTPException(400, f"Produto {item.produto_id} inválido/fornecedor diferente")
        preco = item.preco if item.preco is not None else prod.preco
        subtotal = round(preco * item.quantidade, 2)
        itens.append(ItemPedido(pedido_id=pedido.id, produto_id=prod.id,
                                quantidade=item.quantidade, preco=preco, subtotal=subtotal, motivo=item.motivo))
    pedido.itens = itens
    calcular_total(pedido)
    db.commit(); db.refresh(pedido)
    return pedido

@app.get("/pedidos/{pedido_id}", response_model=PedidoOut, dependencies=[Depends(require_api_key)], tags=["Pedidos"])
def obter_pedido(pedido_id: int, db: Session = Depends(get_db)):
    p = db.get(Pedido, pedido_id)
    if not p: raise HTTPException(404, "Pedido não encontrado")
    return p

@app.get("/pedidos", response_model=List[PedidoOut], dependencies=[Depends(require_api_key)], tags=["Pedidos"])
def listar_pedidos(
    db: Session = Depends(get_db),
    unidade_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    status_eq: Optional[OrderStatus] = None,
    mes: Optional[int] = None,
    ano: Optional[int] = None
):
    q = db.query(Pedido)
    if unidade_id: q = q.filter(Pedido.unidade_id == unidade_id)
    if fornecedor_id: q = q.filter(Pedido.fornecedor_id == fornecedor_id)
    if status_eq: q = q.filter(Pedido.status == status_eq)
    if mes and ano:
        from datetime import datetime as dt
        ini = dt(ano, mes, 1)
        fim = dt(ano + (mes // 12), ((mes % 12) + 1), 1)
        q = q.filter(Pedido.criado_em >= ini, Pedido.criado_em < fim)
    return q.order_by(Pedido.criado_em.desc()).all()

@app.delete("/pedidos/{pedido_id}", dependencies=[Depends(require_api_key)], tags=["Pedidos"])
def deletar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    p = db.get(Pedido, pedido_id)
    if not p: raise HTTPException(404, "Pedido não encontrado")
    db.delete(p); db.commit()
    return {"ok": True}

# --------- ENVIO/APROVAÇÃO/RECEBIMENTO ---------
@app.post("/pedidos/{pedido_id}/enviar", response_model=PedidoOut, dependencies=[Depends(require_api_key)], tags=["Fluxo"])
def enviar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    p = db.get(Pedido, pedido_id)
    if not p: raise HTTPException(404, "Pedido não encontrado")
    if p.status != OrderStatus.RASCUNHO:
        raise HTTPException(400, f"Status atual ({p.status}) não permite enviar")

    calcular_total(p)
    precisa = validar_limites(db, p)
    p.status = OrderStatus.PENDENTE_APROVACAO if precisa else OrderStatus.AUTORIZADO
    db.commit(); db.refresh(p)
    return p

@app.post("/pedidos/{pedido_id}/aprovar", response_model=PedidoOut, dependencies=[Depends(require_api_key)], tags=["Fluxo"])
def aprovar_pedido(pedido_id: int, body: AprovarIn, db: Session = Depends(get_db)):
    p = db.get(Pedido, pedido_id)
    if not p: raise HTTPException(404, "Pedido não encontrado")
    if p.status not in (OrderStatus.PENDENTE_APROVACAO, OrderStatus.REPROVADO):
        raise HTTPException(400, f"Status atual ({p.status}) não permite decisão")

    db.add(Aprovacao(pedido_id=p.id, decisor=body.decisor, aprovado=body.aprovado, motivo=body.motivo))
    if body.aprovado:
        p.status = OrderStatus.AUTORIZADO
    else:
        p.status = OrderStatus.REPROVADO
    db.commit(); db.refresh(p)
    return p

@app.post("/pedidos/{pedido_id}/recebimentos", response_model=PedidoOut, dependencies=[Depends(require_api_key)], tags=["Fluxo"])
def registrar_recebimento(pedido_id: int, body: RecebimentoIn, db: Session = Depends(get_db)):
    p = db.get(Pedido, pedido_id)
    if not p: raise HTTPException(404, "Pedido não encontrado")
    if p.status not in (OrderStatus.AUTORIZADO, OrderStatus.RECEBIDO):
        raise HTTPException(400, f"Status atual ({p.status}) não permite recebimento")
    db.add(Recebimento(pedido_id=p.id, data_recebimento=body.data_recebimento,
                       quantidade_recebida=body.quantidade_recebida, divergencia=body.divergencia))
    p.status = OrderStatus.RECEBIDO
    db.commit(); db.refresh(p)
    return p


if __name__ == "__main__":
    import uvicorn, webbrowser, threading, time
    def _open_browser():
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8000/painel")

    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)