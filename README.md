# Monitor de Internet

Este é um aplicativo de desktop desenvolvido em Python para monitorar a qualidade da conexão de internet. Ele realiza testes de velocidade (Download, Upload, Ping) e perda de pacotes, registrando os dados em um histórico CSV e exibindo um gráfico de tendências.

## Funcionalidades

- **Teste de Velocidade:** Mede a velocidade de Download, Upload e latência (Ping) usando a biblioteca `speedtest-cli`.
- **Perda de Pacotes:** Verifica a estabilidade da conexão medindo a perda de pacotes para um servidor confiável (Google DNS).
- **Dashboard Gráfico:** Exibe um gráfico interativo com o histórico recente das medições de velocidade.
- **Histórico em CSV:** Salva automaticamente todos os resultados em um arquivo `monitoramento_internet.csv` para análise posterior.
- **Informações do Cliente:** Exibe o Provedor de Internet (ISP) e o IP atual.
- **Interface Amigável:** Interface gráfica construída com Tkinter.

## Pré-requisitos

- Python 3.x instalado.

## Instalação

1. Clone este repositório ou baixe os arquivos.
2. Abra o terminal na pasta do projeto.
3. Instale as dependências necessárias executando o comando:

```bash
pip install -r requirements.txt
```

As dependências principais são:
- `speedtest-cli`
- `pandas`
- `matplotlib`

## Como Usar

1. Execute o script principal:

```bash
python "Velocidade Internet.py"
```

2. A interface gráfica será aberta.
3. Clique no botão **"INICIAR TESTE COMPLETO"** para começar as medições.
4. Aguarde o término dos testes (pode levar alguns segundos).
5. Os resultados aparecerão nos cards e o gráfico será atualizado.
6. Para ver o histórico completo, clique em **"📂 Abrir Logs"** ou abra o arquivo `monitoramento_internet.csv` gerado na mesma pasta.

## Notas

- **Erro 403 no Speedtest:** Se você encontrar erros relacionados à API do Speedtest (Forbidden 403), certifique-se de que a biblioteca `speedtest-cli` está atualizada (`pip install speedtest-cli --upgrade`).
- O teste de perda de pacotes utiliza o comando `ping` do sistema operacional.

## Estrutura do Projeto

- `Velocidade Internet.py`: Código fonte principal da aplicação.
- `monitoramento_internet.csv`: Arquivo de log gerado automaticamente (após o primeiro teste).
- `requirements.txt`: Lista de dependências do projeto.
