# Use a imagem Python oficial como base
FROM python:3.11

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo de requisitos e instala as dependências
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copia o restante do código fonte para o contêiner
COPY . .

# Exponha a porta em que o servidor Django estará em execução
EXPOSE 8000

# Comando para iniciar o servidor Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
