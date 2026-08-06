# API - Raízes do Nordeste

### 1. Criar e ativar o ambiente virtual
Criar o ambiente:
python -m venv venv

Ativar (Windows):
venv\Scripts\activate

Ativar (Linux/Mac):
source venv/bin/activate

### 2. Instalar dependências
pip install -r requirements.txt

### 3. Popular o banco de dados
python -m raizes.seed

### 4. Iniciar a aplicação
uvicorn main:app --reload

Acesso: http://127.0.0.1:8000
Swagger: http://127.0.0.1:8000/docs