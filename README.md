# Monitor de Internet

Aplicativo de desktop desenvolvido em Python que **monitora a qualidade da sua conexão de internet em tempo real**. Executa testes de velocidade (download/upload), mede latência (ping) e detecta perda de pacotes, salvando todo o histórico para análise posterior.

## 🎯 O que este projeto faz

- **Testa a velocidade real** da sua internet (download e upload em Mbps)
- **Mede a latência** (ping) até os servidores de teste
- **Detecta perda de pacotes** pingando múltiplos servidores DNS (Google, Cloudflare, OpenDNS)
- **Salva histórico** de todos os testes em CSV para análise
- **Gera gráficos** mostrando a evolução da qualidade ao longo do tempo
- **Compara com suas metas** e indica visualmente se a conexão está boa (verde), regular (amarelo) ou ruim (vermelho)
- **Automatiza testes** em intervalos configuráveis (ex: a cada 30 minutos)
- **Gera relatórios** estatísticos completos em texto

**Ideal para:** Documentar problemas com seu provedor, monitorar a qualidade da conexão ao longo do dia, ou simplesmente acompanhar se você está recebendo o que contratou.

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Versão | Por que foi escolhida |
|------------|--------|----------------------|
| **Python** | 3.7+ | Linguagem versátil, ótima para automação e com bibliotecas maduras para análise de dados |
| **Tkinter** | Nativo | Interface gráfica nativa do Python, sem dependências extras, funciona em qualquer SO |
| **speedtest-cli** | 2.1+ | Biblioteca oficial do Speedtest.net, resultados confiáveis e reconhecidos |
| **pandas** | 1.0+ | Padrão da indústria para manipulação de dados, facilita cálculos estatísticos |
| **matplotlib** | 3.0+ | Biblioteca robusta para gráficos, integra bem com Tkinter |

**Por que essas escolhas?**
- **Python + Tkinter:** Permite criar um executável portátil sem instalações complexas
- **speedtest-cli:** Usa a mesma infraestrutura do site speedtest.net, garantindo precisão
- **pandas + matplotlib:** Combinação clássica para análise e visualização de dados
- **Arquitetura MVC:** Código organizado em classes separadas para fácil manutenção

## 🚀 Funcionalidades

### Testes e Monitoramento
- **Teste de Velocidade:** Mede Download, Upload e Ping usando `speedtest-cli`
- **Perda de Pacotes:** Testa múltiplos servidores (Google DNS, Cloudflare, OpenDNS) para maior confiabilidade
- **Testes Automáticos:** Executa testes periodicamente em intervalos configuráveis
- **Indicadores Visuais:** Cards com cores que indicam qualidade (verde/amarelo/vermelho)

### Análise e Relatórios
- **Dashboard Gráfico:** Visualização interativa do histórico com linhas de meta
- **Estatísticas em Tempo Real:** Médias, mínimos e máximos dos últimos testes
- **Relatórios Detalhados:** Geração automática de análises estatísticas em texto
- **Histórico Persistente:** Todos os dados salvos em CSV com migração automática

### Configuração
- **Menu de Configurações:** Interface gráfica para ajustar todas as metas e parâmetros
- **Arquivo config.json:** Configurações externas sem necessidade de editar código
- **Personalizável:** Metas de velocidade, intervalo de testes, servidores de ping, etc.

## 📋 Pré-requisitos

- **Python 3.7 ou superior** ([Download aqui](https://www.python.org/downloads/))
- **Conexão com a internet** (para os testes funcionarem)
- **Windows, Linux ou macOS** (multiplataforma)

## 🔧 Instalação e Execução

### Passo 1: Clone o repositório
```bash
git clone https://github.com/Nyefall/Monitor-de-Internet.git
cd Monitor-de-Internet
```

### Passo 2: Instale as dependências
```bash
pip install -r requirements.txt
```

### Passo 3: Execute o aplicativo
```bash
python "Velocidade Internet.py"
```

> 💡 **Dica:** Na primeira execução, um arquivo `config.json` será criado automaticamente com valores padrão. Você pode personalizar depois.

### Alternativa: Executar sem clonar
```bash
# Baixe o ZIP do repositório, extraia, e na pasta:
pip install speedtest-cli pandas matplotlib
python "Velocidade Internet.py"
```

## 🎯 Como Usar

### Interface Principal
Após executar, você verá o dashboard com 4 cards de métricas e botões de ação:

```
┌─────────────────────────────────────────────────────┐
│  Dashboard de Monitoramento                         │
├──────────┬──────────┬──────────┬──────────┐        │
│ Download │  Upload  │   Ping   │  Perda   │        │
│ 450 Mbps │ 230 Mbps │  12 ms   │   0%     │        │
└──────────┴──────────┴──────────┴──────────┘        │
│                                                     │
│  [INICIAR TESTE] [Auto] [Relatório] [Config] [Logs]│
│                                                     │
│  📈 Gráfico de histórico aqui                      │
└─────────────────────────────────────────────────────┘
```

### Botões disponíveis
| Botão | Função |
|-------|--------|
| **INICIAR TESTE** | Executa um teste único de velocidade |
| **🔄 Auto** | Liga/desliga testes automáticos periódicos |
| **📊 Relatório** | Gera análise estatística em arquivo .txt |
| **⚙️ Config** | Abre menu para ajustar metas e configurações |
| **📂 Logs** | Abre pasta com CSV e relatórios gerados |

### Personalizando
Clique em **⚙️ Config** para ajustar:
- Metas de Download/Upload/Ping (para os indicadores de cor)
- Intervalo entre testes automáticos
- Servidores de ping para redundância
- Quantidade de testes exibidos no gráfico

## ⚙️ Configurações Disponíveis

Edite via interface gráfica (⚙️ Config) ou diretamente no `config.json`:

```json
{
    "meta_download": 1000,           // Meta de download em Mbps
    "meta_upload": 500,              // Meta de upload em Mbps
    "meta_ping": 20,                 // Latência máxima aceitável (ms)
    "intervalo_auto_teste": 30,      // Minutos entre testes automáticos
    "ping_targets": [                // Servidores para teste de perda
        "8.8.8.8",                   // Google DNS
        "1.1.1.1",                   // Cloudflare DNS
        "208.67.222.222"             // OpenDNS
    ],
    "ping_count": 4,                 // Quantidade de pacotes por servidor
    "grafico_ultimos_n": 30          // Testes exibidos no gráfico
}
```

## 🏗️ Arquitetura (MVC)

O código segue padrão de separação de responsabilidades com **documentação inline completa**:

- **`ConfigManager`:** Gerencia configurações via JSON
- **`InternetTester`:** Executa testes de velocidade e ping (lógica de negócio)
- **`DataManager`:** Gerencia CSV com cache e migração automática
- **`MonitorInternetApp`:** Interface gráfica e coordenação (apenas UI)

**Qualidade do Código:**
- ✅ 100% documentado (docstrings + comentários explicativos)
- ✅ Type hints em todas funções públicas
- ✅ Sem imports não utilizados
- ✅ ~1000 linhas bem organizadas em 4 classes
- ✅ Thread-safe para UI responsiva

## 📁 Estrutura de Arquivos

```
Monitor-de-Internet/
├── Velocidade Internet.py      # Código principal (~1000 linhas, 4 classes)
├── config.json                  # Configurações (gerado automaticamente)
├── monitoramento_internet.csv   # Dados históricos (gerado após 1º teste)
├── relatorio_*.txt             # Relatórios gerados
├── requirements.txt            # Dependências Python
├── README.md                   # Este arquivo
├── MELHORIAS.md                # Documentação das melhorias implementadas
├── .gitignore                  # Arquivos ignorados pelo Git
└── .gitattributes              # Configuração Git
```

## 📚 Documentação

- **README.md:** Guia de uso e instalação
- **MELHORIAS.md:** Detalhamento técnico das refatorações e melhorias implementadas
- **Código fonte:** 100% documentado com docstrings e comentários explicativos

## 🐛 Solução de Problemas

**Erro 403 no Speedtest:**
```bash
pip install speedtest-cli --upgrade
```

**Ping não funciona:**
- Verifique firewall
- Teste com diferentes servidores no menu Config

**CSV corrompido:**
- O sistema faz migração automática
- Em caso de problema, delete o CSV e rode novo teste

## 🤝 Contribuindo

Contribuições são bem-vindas! Abra issues ou pull requests.

## 📄 Licença

MIT License
