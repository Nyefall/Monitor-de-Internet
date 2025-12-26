# Monitor de Internet

Aplicativo de desktop profissional desenvolvido em Python para monitorar a qualidade da conexão de internet com arquitetura MVC, testes automatizados e configurações personalizáveis.

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

- Python 3.7 ou superior

## 🔧 Instalação

1. Clone este repositório:
```bash
git clone https://github.com/Nyefall/Monitor-de-Internet.git
cd Monitor-de-Internet
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## 🎯 Como Usar

1. Execute o aplicativo:
```bash
python "Velocidade Internet.py"
```

2. Na primeira execução, um arquivo `config.json` será criado com valores padrão.

3. **Botões disponíveis:**
   - **INICIAR TESTE:** Executa teste único
   - **🔄 Auto:** Ativa/desativa testes automáticos periódicos
   - **📊 Relatório:** Gera análise estatística completa
   - **⚙️ Config:** Abre menu de configurações
   - **📂 Logs:** Abre pasta com arquivos CSV e relatórios

4. **Personalize as configurações** via menu Config:
   - Metas de Download/Upload/Ping
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

Este projeto é de código aberto.
