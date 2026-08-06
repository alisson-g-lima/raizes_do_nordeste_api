from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime

from raizes.extensions import engine, Base
from raizes.routes import pedidos, auth, produtos, auditoria, unidades, promocoes, estoque

app = FastAPI(
    title="API Raízes do Nordeste",
    description="Projeto Multidisciplinar - Trilha Back-End",
    version="1.0.0"
)

@app.exception_handler(StarletteHTTPException)
async def interceptar_erros_http(requisicao: Request, excecao: StarletteHTTPException):
    mapa_erros = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        500: "INTERNAL_SERVER_ERROR"
    }
    
    titulo_erro = mapa_erros.get(excecao.status_code, "HTTP_ERROR")
    
    return JSONResponse(
        status_code=excecao.status_code,
        content={
            "error": titulo_erro,
            "message": str(excecao.detail),
            "details": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "path": requisicao.url.path
        }
    )

@app.exception_handler(RequestValidationError)
async def interceptar_dados_invalidos(requisicao: Request, excecao: RequestValidationError):
    trilha_de_erros = []
    
    for problema in excecao.errors():
        campo_afetado = str(problema.get("loc")[-1]) if problema.get("loc") else "unknown"
        trilha_de_erros.append({
            "field": campo_afetado,
            "issue": problema.get("msg")
        })

    return JSONResponse(
        status_code=422,
        content={
            "error": "UNPROCESSABLE_ENTITY",
            "message": "Erro na validação nos dados enviados.",
            "details": trilha_de_erros,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "path": requisicao.url.path
        }
    )

app.include_router(auth.router)
app.include_router(produtos.router)
app.include_router(estoque.router)
app.include_router(pedidos.router)
app.include_router(auditoria.router)
app.include_router(unidades.router)
app.include_router(promocoes.router)

@app.get("/")
def root():
    return {"mensagem": "Bem vindo a API Raízes do Nordeste."}