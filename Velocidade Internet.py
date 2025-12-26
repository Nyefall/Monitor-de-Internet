# ============================================================================
# MONITOR DE INTERNET - Sistema de Monitoramento de Velocidade e Qualidade
# ============================================================================
# Funcionalidades:
# - Testes de velocidade (download/upload) via speedtest-cli
# - Medição de ping e perda de pacotes em múltiplos servidores
# - Armazenamento de histórico em CSV
# - Visualização gráfica dos resultados
# - Configuração via JSON (sem editar código)
# - Testes automáticos com intervalo configurável
# ============================================================================

# Bibliotecas padrão do Python
import os              # Manipulação de arquivos e diretórios
import csv             # Leitura/escrita de arquivos CSV
import datetime        # Manipulação de datas e horas
import subprocess      # Execução de comandos externos (ping, speedtest)
import threading       # Execução assíncrona de testes (não trava a UI)
import re              # Regex para extrair dados do ping
import json            # Manipulação de config.json
import sys             # Acesso ao executável Python

# Interface gráfica Tkinter
import tkinter as tk
from tkinter import messagebox, ttk

# Análise de dados e gráficos
import pandas as pd                                      # Manipulação de DataFrames (CSV)
import matplotlib.pyplot as plt                          # Criação de gráficos
import matplotlib.dates as mdates                        # Formatação de datas nos gráficos
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # Integração matplotlib + tkinter

# Type hints para melhor documentação
from typing import Dict, Optional, Tuple

# ============================================================================
# GERENCIADOR DE CONFIGURAÇÕES
# ============================================================================
# Responsabilidades:
# - Carregar/salvar configurações do arquivo config.json
# - Criar arquivo com valores padrão se não existir
# - Permitir atualização de configurações sem reiniciar
# ============================================================================

class ConfigManager:
    """Gerencia configurações do aplicativo via arquivo JSON"""
    
    # Valores padrão - usados na primeira execução ou se config.json estiver corrompido
    DEFAULT_CONFIG = {
        "meta_download": 1000,           # Meta de download em Mbps (para indicador visual)
        "meta_upload": 500,              # Meta de upload em Mbps
        "meta_ping": 20,                 # Meta de ping em ms (menor é melhor)
        "intervalo_auto_teste": 30,      # Intervalo entre testes automáticos (minutos)
        "ping_targets": ["8.8.8.8", "1.1.1.1", "208.67.222.222"],  # Servidores para teste de perda de pacotes
        "ping_count": 4,                 # Quantidade de pacotes por servidor
        "grafico_ultimos_n": 30          # Quantos testes exibir no gráfico
    }
    
    def __init__(self, config_path: str = "config.json"):
        """Inicializa gerenciador e carrega configurações"""
        self.config_path = config_path
        self.config = self.carregar_config()
    
    def carregar_config(self) -> Dict:
        """Carrega configurações do JSON ou cria com valores padrão"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge com defaults para garantir que todas as chaves existam
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded_config)
                    return config
            except Exception as e:
                print(f"Erro ao carregar config: {e}. Usando padrão.")
                return self.DEFAULT_CONFIG.copy()
        else:
            # Cria arquivo de configuração padrão
            self.salvar_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()
    
    def salvar_config(self, config: Dict = None) -> bool:
        """Salva configurações no arquivo JSON"""
        try:
            config_to_save = config if config else self.config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erro ao salvar config: {e}")
            return False
    
    def atualizar(self, chave: str, valor) -> bool:
        """Atualiza uma configuração específica"""
        self.config[chave] = valor
        return self.salvar_config()
    
    def get(self, chave: str, default=None):
        """Obtém valor de configuração"""
        return self.config.get(chave, default)


# ============================================================================
# TESTADOR DE INTERNET
# ============================================================================
# Responsabilidades:
# - Executar speedtest usando speedtest-cli via subprocess
# - Medir perda de pacotes em múltiplos servidores DNS (redundância)
# - Extrair e parsear resultados usando regex
# - Retornar dados estruturados (dicionários)
# ============================================================================

class InternetTester:
    """Responsável por executar testes de velocidade e qualidade da conexão"""
    
    def __init__(self, config_manager: ConfigManager):
        """Inicializa testador com referência ao gerenciador de config"""
        self.config = config_manager
    
    def medir_perda_pacotes(self) -> int:
        """
        Testa perda de pacotes em múltiplos servidores para maior confiabilidade.
        
        Retorna:
            int: Porcentagem média de perda (0-100) ou -1 em caso de erro total
        """
        ping_targets = self.config.get('ping_targets', ["8.8.8.8", "1.1.1.1"])
        ping_count = self.config.get('ping_count', 4)
        
        resultados = []
        
        for target in ping_targets:
            try:
                param = '-n' if os.name == 'nt' else '-c'
                comando = ['ping', param, str(ping_count), target]
                
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                processo = subprocess.Popen(
                    comando, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo, 
                    text=True
                )
                
                try:
                    saida, _ = processo.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    processo.kill()
                    print(f"Timeout ao pingar {target}")
                    continue
                
                # Debug: mostra saída COMPLETA do ping (útil para troubleshooting)
                print(f"\n=== Ping {target} ===")
                print(saida)  # Saída completa para análise
                print("=" * 50)
                
                # Procura por perda de pacotes usando múltiplos padrões regex
                # Windows PT-BR tem formato diferente do inglês, daí múltiplos padrões
                patterns = [
                    r'Perdidos\s*=\s*\d+\s*\((\d+)%',  # "Perdidos = 0 (0% de perda)" Windows PT-BR
                    r'(\d+)%\s*de perda',                # "0% de perda" genérico português
                    r'(\d+)%\s*perdidos',                # "0% perdidos"
                    r'(\d+)%\s*loss',                    # "0% loss" (inglês)
                    r'\((\d+)%.*?lost\)',                # "(0% lost)" formato alternativo
                ]
                
                match = None
                for pattern in patterns:
                    match = re.search(pattern, saida, re.IGNORECASE)
                    if match:
                        perda = int(match.group(1))
                        resultados.append(perda)
                        print(f"\u2705 Ping {target}: {perda}% perda (padrão: {pattern})")
                        break
                
                if not match:
                    print(f"\u26a0\ufe0f Não foi possível extrair perda de pacotes de {target}")
            except Exception as e:
                print(f"Erro ao pingar {target}: {e}")
                continue
        
        # Retorna a média de perda, ou 0 se pelo menos um sucedeu
        if resultados:
            return int(sum(resultados) / len(resultados))
        
        # Se todos falharam, tenta um ping simples ao Google como fallback
        if not resultados:
            print("\n⚠\ufe0f Tentando fallback: ping simples ao 8.8.8.8...")
            try:
                param = '-n' if os.name == 'nt' else '-c'
                comando = ['ping', param, '2', '8.8.8.8']
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                processo = subprocess.Popen(comando, stdout=subprocess.PIPE, 
                                           stderr=subprocess.PIPE, startupinfo=startupinfo, text=True)
                saida, _ = processo.communicate(timeout=5)
                
                print("=== Fallback Output ===")
                print(saida)  # Saída completa
                print("=" * 50)
                
                patterns = [
                    r'Perdidos\s*=\s*\d+\s*\((\d+)%',  # Windows PT-BR
                    r'(\d+)%\s*de perda',
                    r'(\d+)%\s*perdidos',
                    r'(\d+)%\s*loss',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, saida, re.IGNORECASE)
                    if match:
                        print(f"\u2705 Fallback sucesso: {match.group(1)}% perda")
                        return int(match.group(1))
                
                print("⚠\ufe0f Nenhum padrão de regex encontrado no fallback")
            except Exception as e:
                print(f"❌ Fallback falhou: {e}")
        
        print(f"\n📊 Resultados finais: {resultados}")
        return -1  # Só retorna erro (-1) se todos os servidores falharem
    
    def executar_speedtest(self) -> Optional[Dict]:
        """
        Executa teste de velocidade usando speedtest-cli.
        
        Processo:
        1. Chama 'python -m speedtest --secure --json' via subprocess
        2. Aguarda até 120 segundos (testes podem demorar)
        3. Parseia JSON retornado
        4. Converte bits/s para Mbps (divisão por 1.000.000)
        
        Retorna:
            Dict com keys: download, upload, ping, isp, ip
            None em caso de erro
        """
        try:
            # Comando: python -m speedtest --secure --json
            cmd = [sys.executable, '-m', 'speedtest', '--secure', '--json']
            
            # No Windows, esconde janela do CMD
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            processo = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                startupinfo=startupinfo, 
                text=True
            )
            
            # Aguarda conclusão (timeout 120s)
            stdout, stderr = processo.communicate(timeout=120)
            
            if processo.returncode != 0:
                raise Exception(f"Erro CLI: {stderr}")

            # Parseia JSON retornado pelo speedtest-cli
            resultado = json.loads(stdout)
            
            # Extrai e converte dados (bits -> Mbps)
            return {
                'download': resultado['download'] / 1_000_000,  # Converte bits/s para Mbps
                'upload': resultado['upload'] / 1_000_000,      # Converte bits/s para Mbps
                'ping': resultado['ping'],                       # Já vem em ms
                'isp': resultado['client'].get('isp', 'Desconhecido'),  # Provedor de internet
                'ip': resultado['client'].get('ip', 'Desconhecido')     # IP público do cliente
            }
        except Exception as e:
            raise Exception(f"Falha no speedtest: {str(e)}")


# ============================================================================
# GERENCIADOR DE DADOS (CSV)
# ============================================================================
# Responsabilidades:
# - Salvar testes no arquivo CSV (append)
# - Ler CSV e converter para DataFrame pandas
# - Calcular estatísticas (média, mínimo, máximo)
# - Sistema de cache para melhor performance
# - Migração automática de formato antigo (retrocompatibilidade)
# ============================================================================

class DataManager:
    """Gerencia salvamento, leitura e migração de dados CSV"""
    
    # Colunas do arquivo CSV - ordem importa!
    COLUNAS = [
        "Data e Hora",           # Formato: dd/mm/YYYY HH:MM:SS
        "Download (Mbps)",       # Velocidade de download
        "Upload (Mbps)",         # Velocidade de upload
        "Ping (ms)",             # Latência HTTP até servidor speedtest
        "Perda Pacotes (%)",     # % de pacotes ICMP perdidos (0-100)
        "Provedor",              # Nome do ISP
        "IP Cliente"             # IP público
    ]
    
    def __init__(self, arquivo_csv: str):
        self.arquivo_csv = arquivo_csv
        self.cache = None            # DataFrame em memória (evita ler CSV toda hora)
        self.cache_timestamp = 0     # Timestamp do arquivo quando foi cacheado
    
    def salvar_teste(self, data_hora: str, down: float, up: float, ping: float, 
                     packet_loss: int, isp: str, ip: str) -> Tuple[bool, str]:
        """
        Salva resultado de teste no CSV (modo append).
        
        Parâmetros:
            data_hora: String no formato "dd/mm/YYYY HH:MM:SS"
            down/up/ping: Valores numéricos (serão formatados com vírgula)
            packet_loss: Inteiro 0-100 (porcentagem)
            isp/ip: Strings com informações do cliente
        
        Retorna:
            Tupla (sucesso: bool, mensagem: str)
        """
        novo_arquivo = not os.path.exists(self.arquivo_csv)
        
        try:
            # Migração de formato antigo se necessário
            if not novo_arquivo:
                self._verificar_migrar_formato()

            with open(self.arquivo_csv, mode='a', newline='', encoding='utf-8-sig') as f:
                escritor = csv.writer(f, delimiter=';')
                if novo_arquivo:
                    escritor.writerow(self.COLUNAS)
                
                escritor.writerow([
                    data_hora, 
                    f"{down:.2f}".replace('.', ','), 
                    f"{up:.2f}".replace('.', ','), 
                    f"{ping:.2f}".replace('.', ','),
                    f"{packet_loss}",
                    isp,
                    ip
                ])
            
            # Invalida cache
            self.cache = None
            return True, "Sucesso"
            
        except PermissionError:
            return False, "O arquivo está aberto em outro programa. Feche-o e tente novamente."
        except Exception as e:
            return False, f"Erro ao salvar: {str(e)}"
    
    def _verificar_migrar_formato(self):
        """Verifica e migra formato antigo de CSV se necessário"""
        try:
            with open(self.arquivo_csv, 'r', encoding='utf-8-sig') as f:
                cabecalho_atual = f.readline().strip().split(';')
            
            if len(cabecalho_atual) < len(self.COLUNAS):
                df_antigo = pd.read_csv(self.arquivo_csv, delimiter=';', decimal=',')
                for col in self.COLUNAS:
                    if col not in df_antigo.columns:
                        df_antigo[col] = "N/A"
                df_antigo.to_csv(self.arquivo_csv, sep=';', decimal=',', 
                               index=False, encoding='utf-8-sig')
        except Exception as e:
            print(f"Erro na migração: {e}")
    
    def carregar_dados(self, force_reload: bool = False) -> Optional[pd.DataFrame]:
        """Carrega dados do CSV com sistema de cache"""
        try:
            if not os.path.exists(self.arquivo_csv):
                return None
            
            # Verifica se precisa recarregar
            arquivo_mtime = os.path.getmtime(self.arquivo_csv)
            if not force_reload and self.cache is not None and arquivo_mtime == self.cache_timestamp:
                return self.cache
            
            # Carrega e processa
            df = pd.read_csv(self.arquivo_csv, delimiter=';', decimal=',')
            if not df.empty:
                df['Data e Hora'] = pd.to_datetime(
                    df['Data e Hora'], 
                    format='%d/%m/%Y %H:%M:%S', 
                    errors='coerce'
                )
                df = df.dropna(subset=['Data e Hora'])
                
                self.cache = df
                self.cache_timestamp = arquivo_mtime
            
            return df
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
            return None
    
    def obter_estatisticas(self, ultimos_n: int = 10) -> Optional[Dict]:
        """Calcula estatísticas dos últimos N testes"""
        df = self.carregar_dados()
        if df is None or df.empty:
            return None
        
        df_recente = df.tail(ultimos_n)
        
        return {
            'total_testes': len(df),
            'down_mean': df_recente['Download (Mbps)'].mean(),
            'down_min': df_recente['Download (Mbps)'].min(),
            'down_max': df_recente['Download (Mbps)'].max(),
            'down_std': df_recente['Download (Mbps)'].std(),
            'up_mean': df_recente['Upload (Mbps)'].mean(),
            'up_min': df_recente['Upload (Mbps)'].min(),
            'up_max': df_recente['Upload (Mbps)'].max(),
            'ping_mean': df_recente['Ping (ms)'].mean(),
            'ping_min': df_recente['Ping (ms)'].min(),
            'ping_max': df_recente['Ping (ms)'].max(),
            'data_primeiro': df.iloc[0]['Data e Hora'],
            'data_ultimo': df.iloc[-1]['Data e Hora']
        }


# ============================================================================
# INTERFACE GRÁFICA (UI)
# ============================================================================
# Responsabilidades:
# - Criar e gerenciar toda a interface Tkinter
# - Coordenar chamadas entre ConfigManager, InternetTester e DataManager
# - Executar testes em thread separada (não trava UI)
# - Atualizar cards, gráficos e estatísticas
# - Gerenciar testes automáticos com timer
# ============================================================================

class MonitorInternetApp:
    """Interface gráfica do monitor de internet - Coordenação e UI"""
    
    def __init__(self, root):
        """Inicializa aplicativo e componentes"""
        self.root = root
        self.root.title("Monitor Internet")
        self.root.geometry("900x750")
        self.root.configure(bg="#f0f0f0")

        # Inicializa componentes do padrão MVC
        self.pasta_script = os.path.dirname(os.path.abspath(__file__))
        self.config = ConfigManager(os.path.join(self.pasta_script, "config.json"))        # Model: Configurações
        self.tester = InternetTester(self.config)                                          # Controller: Testes
        self.data_manager = DataManager(os.path.join(self.pasta_script, 'monitoramento_internet.csv'))  # Model: Dados
        
        # Controle de estado da aplicação
        self.auto_teste_ativo = False    # Flag para testes automáticos
        self.auto_teste_job = None       # ID do timer do Tkinter (para cancelar)
        self.testando = False            # Flag para evitar múltiplos testes simultâneos

        # Constrói interface e carrega dados iniciais
        self.setup_ui()
        self.carregar_ultimo_teste()
        self.atualizar_grafico_embedded()

    def setup_ui(self):
        """Constrói toda a interface gráfica (widgets Tkinter)"""
        
        # Configura estilo visual dos componentes ttk
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#333")
        style.configure("Card.TFrame", background="white", relief="raised")
        
        # Container Principal
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill="both", expand=True)

        # Cabeçalho
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(header_frame, text="Dashboard de Monitoramento", style="Header.TLabel").pack(side="left")
        self.lbl_status = ttk.Label(header_frame, text="Pronto", foreground="gray")
        self.lbl_status.pack(side="right", padx=10)

        # Info do Cliente (ISP e IP)
        self.lbl_client_info = ttk.Label(main_frame, text="Provedor: -- | IP: --", font=("Segoe UI", 9), foreground="#555")
        self.lbl_client_info.pack(fill="x", pady=(0, 5))
        
        # Estatísticas resumidas
        self.lbl_stats = ttk.Label(main_frame, text="Carregando estatísticas...", font=("Segoe UI", 9), foreground="#888")
        self.lbl_stats.pack(fill="x", pady=(0, 10))

        # Cards de Status - Grid 4 colunas (Download, Upload, Ping, Perda)
        cards_frame = ttk.Frame(main_frame)
        cards_frame.pack(fill="x", pady=(0, 20))
        cards_frame.columnconfigure(0, weight=1)  # Card Download
        cards_frame.columnconfigure(1, weight=1)  # Card Upload
        cards_frame.columnconfigure(2, weight=1)  # Card Ping
        cards_frame.columnconfigure(3, weight=1)  # Card Perda Pacotes

        # Card Download (velocidade de download)
        self.card_down = self.criar_card(cards_frame, "Download", "⬇️", 0)
        # Card Upload (velocidade de upload)
        self.card_up = self.criar_card(cards_frame, "Upload", "⬆️", 1)
        # Card Ping (latência HTTP até servidor speedtest, NÃO é o mesmo que ping ICMP)
        self.card_ping = self.criar_card(cards_frame, "Ping (HTTP)", "📶", 2)
        # Card Perda de Pacotes (% de pacotes ICMP perdidos medido separadamente)
        self.card_loss = self.criar_card(cards_frame, "Perda Pcts", "❌", 3)

        # Barra de Progresso
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill="x", pady=(0, 10))

        # Botões
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(0, 10))
        
        self.btn_testar = tk.Button(btn_frame, text="INICIAR TESTE", command=self.iniciar_teste, 
                                    bg="#4CAF50", fg="white", font=("Segoe UI", 11, "bold"), 
                                    relief="flat", padx=20, pady=10, cursor="hand2")
        self.btn_testar.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_auto = tk.Button(btn_frame, text="🔄 Auto (OFF)", command=self.toggle_auto_teste, 
                                 bg="#9E9E9E", fg="white", font=("Segoe UI", 10), 
                                 relief="flat", padx=15, cursor="hand2")
        self.btn_auto.pack(side="left", padx=(0, 5))
        
        self.btn_relatorio = tk.Button(btn_frame, text="📊 Relatório", command=self.gerar_relatorio, 
                                       bg="#FF9800", fg="white", font=("Segoe UI", 10), 
                                       relief="flat", padx=15, cursor="hand2")
        self.btn_relatorio.pack(side="left", padx=(0, 5))
        
        self.btn_config = tk.Button(btn_frame, text="⚙️ Config", command=self.abrir_configuracoes, 
                                    bg="#9C27B0", fg="white", font=("Segoe UI", 10), 
                                    relief="flat", padx=15, cursor="hand2")
        self.btn_config.pack(side="left", padx=(0, 5))

        self.btn_pasta = tk.Button(btn_frame, text="📂 Logs", command=self.abrir_pasta, 
                                   bg="#2196F3", fg="white", font=("Segoe UI", 10), 
                                   relief="flat", padx=15, cursor="hand2")
        self.btn_pasta.pack(side="right")

        # Área do Gráfico
        self.graph_frame = ttk.Frame(main_frame)
        self.graph_frame.pack(fill="both", expand=True)
        
        # Placeholder para o gráfico
        self.lbl_no_data = ttk.Label(self.graph_frame, text="Nenhum dado histórico disponível.", font=("Segoe UI", 12))
        self.lbl_no_data.pack(expand=True)

    def criar_card(self, parent, titulo, icone, col):
        """
        Cria um card visual (retângulo branco com título e valor).
        
        Estrutura:
        - Frame branco com borda
        - Label superior: emoji + título
        - Label inferior: valor numérico (--) em negrito
        
        Retorna: Label do valor (para atualizar depois)
        """
        frame = tk.Frame(parent, bg="white", bd=1, relief="solid")
        frame.grid(row=0, column=col, padx=5, sticky="ew")
        
        lbl_titulo = tk.Label(frame, text=f"{icone} {titulo}", bg="white", fg="#666", font=("Segoe UI", 10))
        lbl_titulo.pack(pady=(10, 0))
        lbl_valor = tk.Label(frame, text="--", bg="white", fg="#333", font=("Segoe UI", 16, "bold"))
        lbl_valor.pack(pady=(5, 10))
        
        # Retorna frame, label do título e label do valor para permitir colorir depois
        frame.lbl_titulo = lbl_titulo
        frame.lbl_valor = lbl_valor
        return lbl_valor

    def iniciar_teste(self):
        if self.testando:
            messagebox.showwarning("Atenção", "Um teste já está em andamento.")
            return
        
        self.testando = True
        self.btn_testar.config(state="disabled", text="Testando...", bg="#a5d6a7")
        self.lbl_status.config(text="Iniciando testes...", foreground="blue")
        self.progress.start(10)
        threading.Thread(target=self.executar_teste_thread, daemon=True).start()

    def medir_perda_pacotes(self):
        try:
            # Executa ping para o Google DNS (8.8.8.8) com 4 pacotes
            param = '-n' if os.name == 'nt' else '-c'
            comando = ['ping', param, '4', '8.8.8.8']
            
            # No Windows, precisamos esconder a janela do CMD
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                      startupinfo=startupinfo, text=True)
            saida, _ = processo.communicate()
            
            # Procura por "x% loss" ou "x% de perda"
            match = re.search(r'(\d+)% loss', saida) or re.search(r'(\d+)% de perda', saida)
            if match:
                return int(match.group(1))
            return 0
        except Exception:
            return -1 # Erro ao medir

    def executar_teste_thread(self):
        """
        Executa testes em thread separada (não trava a UI).
        
        Fluxo:
        1. Speedtest (pode levar 30-60s)
        2. Teste de perda de pacotes (5-10s por servidor)
        3. Salva no CSV
        4. Atualiza UI usando root.after() (thread-safe)
        
        Importante: Nunca atualizar UI diretamente da thread!
        Sempre usar root.after(0, lambda: ...) para voltar à thread principal.
        """
        try:
            # 1. Executa Speedtest (lento)
            self.root.after(0, lambda: self.lbl_status.config(text="Executando Speedtest (pode demorar)..."))
            resultado_speed = self.tester.executar_speedtest()
            
            # 2. Mede perda de pacotes (rápido)
            self.root.after(0, lambda: self.lbl_status.config(text="Medindo Perda de Pacotes..."))
            packet_loss = self.tester.medir_perda_pacotes()
            
            # Prepara dados
            data_hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            # Salva no CSV
            sucesso, msg = self.data_manager.salvar_teste(
                data_hora,
                resultado_speed['download'],
                resultado_speed['upload'],
                resultado_speed['ping'],
                packet_loss,
                resultado_speed['isp'],
                resultado_speed['ip']
            )
            
            # Finaliza na thread principal
            self.root.after(0, lambda: self.finalizar_teste(
                sucesso, msg, data_hora,
                resultado_speed['download'],
                resultado_speed['upload'],
                resultado_speed['ping'],
                packet_loss,
                resultado_speed['isp'],
                resultado_speed['ip']
            ))

        except Exception as e:
            error_message = str(e)
            if "403" in error_message:
                error_message = "Erro 403: Falha na API do Speedtest. Tente atualizar: 'pip install speedtest-cli --upgrade'"
            self.root.after(0, lambda: self.finalizar_teste(False, error_message))

    def finalizar_teste(self, sucesso, msg, data_hora=None, down=0, up=0, ping=0, packet_loss=0, isp="--", ip="--"):
        self.testando = False
        self.progress.stop()
        self.btn_testar.config(state="normal", text="INICIAR TESTE", bg="#4CAF50")

        if sucesso:
            self.lbl_status.config(text=f"Último Teste: {data_hora}", foreground="green")
            self.lbl_client_info.config(text=f"Provedor: {isp} | IP: {ip}")
            
            # Atualiza cards com indicadores visuais de qualidade
            meta_down = self.config.get('meta_download', 1000)
            meta_up = self.config.get('meta_upload', 500)
            meta_ping = self.config.get('meta_ping', 20)
            
            self.atualizar_card_com_cor(self.card_down, down, meta_down, f"{down:.1f} Mbps", maior_melhor=True)
            self.atualizar_card_com_cor(self.card_up, up, meta_up, f"{up:.1f} Mbps", maior_melhor=True)
            self.atualizar_card_com_cor(self.card_ping, ping, meta_ping, f"{ping:.0f} ms", maior_melhor=False)
            
            loss_text = f"{packet_loss}%" if packet_loss >= 0 else "Erro"
            loss_color = "red" if packet_loss > 0 else "#333"
            self.card_loss.config(text=loss_text, fg=loss_color)
            
            # Atualiza gráfico e estatísticas
            self.atualizar_grafico_embedded()
            self.atualizar_estatisticas()
        else:
            self.lbl_status.config(text="Erro no teste", foreground="red")
            messagebox.showerror("Erro", f"Falha: {msg}")

    def atualizar_grafico_embedded(self):
        """Atualiza gráfico embedded usando DataManager"""
        # Limpa a área do gráfico
        for widget in self.graph_frame.winfo_children():
            widget.destroy()

        df = self.data_manager.carregar_dados()
        if df is None or df.empty:
            ttk.Label(self.graph_frame, text="Execute um teste para ver o histórico.", 
                     font=("Segoe UI", 12)).pack(expand=True)
            return

        try:
            # Pega últimos N registros (configurável)
            ultimos_n = self.config.get('grafico_ultimos_n', 30)
            df_plot = df.tail(ultimos_n).copy()

            # Cria a figura do Matplotlib
            fig = plt.Figure(figsize=(6, 4), dpi=100)
            ax = fig.add_subplot(111)
            
            ax.plot(df_plot['Data e Hora'], df_plot['Download (Mbps)'], label='Download', color='#2196F3', marker='o', linewidth=2, markersize=4)
            ax.plot(df_plot['Data e Hora'], df_plot['Upload (Mbps)'], label='Upload', color='#FF9800', marker='x', linestyle='--', linewidth=1.5, markersize=5)

            # Linhas de meta (configuráveis)
            meta_down = self.config.get('meta_download', 1000)
            meta_up = self.config.get('meta_upload', 500)
            ax.axhline(y=meta_down, color='r', linestyle=':', alpha=0.5, label=f'Meta Down ({meta_down})')
            ax.axhline(y=meta_up, color='orange', linestyle=':', alpha=0.3, label=f'Meta Up ({meta_up})')
            
            ax.set_title(f'Histórico Recente (Últimos {len(df_plot)} testes)', fontsize=10)
            ax.set_ylabel('Velocidade (Mbps)', fontsize=9)
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)
            
            # Formatação de data
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
            fig.autofmt_xdate()
            
            # Ajuste de layout
            fig.tight_layout()

            # Embed no Tkinter
            canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
        except Exception as e:
            ttk.Label(self.graph_frame, text=f"Erro ao carregar gráfico: {e}").pack()

    def carregar_ultimo_teste(self):
        """Carrega e exibe dados do último teste realizado usando DataManager"""
        try:
            df = self.data_manager.carregar_dados()
            if df is not None and not df.empty:
                ultimo = df.iloc[-1]
                self.lbl_client_info.config(
                    text=f"Provedor: {ultimo.get('Provedor', '--')} | IP: {ultimo.get('IP Cliente', '--')}"
                )
                self.atualizar_estatisticas()
        except Exception as e:
            print(f"Erro ao carregar último teste: {e}")
    
    def atualizar_card_com_cor(self, card_label, valor, meta, texto, maior_melhor=True):
        """
        Atualiza card com cores baseadas na performance (verde/amarelo/vermelho).
        
        Lógica:
        - Verde: >= 80% da meta
        - Amarelo: >= 50% da meta
        - Vermelho: < 50% da meta
        
        Para ping (menor é melhor), inverte o cálculo.
        """
        card_label.config(text=texto)
        
        # Calcula performance relativa (0.0 a 1.0+)
        if maior_melhor:  # Download/Upload - maior é melhor
            performance = (valor / meta) if meta > 0 else 0
            cor_fundo = "#C8E6C9" if performance >= 0.8 else "#FFECB3" if performance >= 0.5 else "#FFCDD2"
        else:  # Ping - menor é melhor
            performance = (meta / valor) if valor > 0 else 0
            cor_fundo = "#C8E6C9" if performance >= 0.8 else "#FFECB3" if performance >= 0.5 else "#FFCDD2"
        
        # Atualiza cor de fundo do card (frame + labels)
        parent_frame = card_label.master
        parent_frame.config(bg=cor_fundo)
        if hasattr(parent_frame, 'lbl_titulo'):
            parent_frame.lbl_titulo.config(bg=cor_fundo)
        card_label.config(bg=cor_fundo)
    
    def atualizar_estatisticas(self):
        """Calcula e exibe estatísticas usando DataManager"""
        try:
            stats = self.data_manager.obter_estatisticas(ultimos_n=10)
            if stats is None:
                self.lbl_stats.config(text="Sem dados para estatísticas")
                return
            
            texto_stats = (f"📈 Últimos 10 testes - Download: Média {stats['down_mean']:.1f} | "
                          f"Min {stats['down_min']:.1f} | Max {stats['down_max']:.1f} Mbps | "
                          f"Ping Médio: {stats['ping_mean']:.0f}ms | Total: {stats['total_testes']}")
            self.lbl_stats.config(text=texto_stats)
        except Exception as e:
            self.lbl_stats.config(text=f"Erro ao calcular estatísticas: {e}")
    
    def toggle_auto_teste(self):
        """
        Liga/desliga testes automáticos periódicos.
        
        Quando ativado:
        - Agenda testes usando root.after() (timer do Tkinter)
        - Intervalo configurável em config.json (intervalo_auto_teste)
        """
        self.auto_teste_ativo = not self.auto_teste_ativo
        intervalo = self.config.get('intervalo_auto_teste', 30)  # Minutos
        
        if self.auto_teste_ativo:
            self.btn_auto.config(text="🔄 Auto (ON)", bg="#4CAF50")
            self.lbl_status.config(text=f"Teste automático ativo (a cada {intervalo}min)", foreground="blue")
            self.agendar_proximo_teste()
        else:
            self.btn_auto.config(text="🔄 Auto (OFF)", bg="#9E9E9E")
            if self.auto_teste_job:  # Cancela timer pendente
                self.root.after_cancel(self.auto_teste_job)
                self.auto_teste_job = None
            self.lbl_status.config(text="Teste automático desativado", foreground="gray")
    
    def agendar_proximo_teste(self):
        """Agenda o próximo teste automático usando root.after()"""
        if self.auto_teste_ativo:
            intervalo = self.config.get('intervalo_auto_teste', 30)  # Minutos
            intervalo_ms = intervalo * 60 * 1000  # Converte para milissegundos
            # Salva ID do job para poder cancelar depois
            self.auto_teste_job = self.root.after(intervalo_ms, self.executar_teste_automatico)
    
    def executar_teste_automatico(self):
        """Callback do timer - executa teste se não houver outro em andamento"""
        if not self.testando:
            self.iniciar_teste()
        self.agendar_proximo_teste()  # Agenda o próximo
    
    def gerar_relatorio(self):
        """
        Gera relatório estatístico em texto plano.
        
        Conteúdo:
        - Período analisado (primeiro/último teste)
        - Estatísticas de download/upload/ping (média, min, max, desvio padrão)
        - Porcentagem de testes abaixo da meta
        - Análise comparativa com meta contratada
        """
        try:
            # Obtém estatísticas de TODOS os testes (não só os últimos 10)
            stats = self.data_manager.obter_estatisticas(ultimos_n=len(self.data_manager.carregar_dados() or []))
            df = self.data_manager.carregar_dados()
            
            if df is None or df.empty or stats is None:
                messagebox.showinfo("Relatório", "Nenhum dado disponível para gerar relatório.")
                return
            
            # Testes abaixo da meta
            meta_down = self.config.get('meta_download', 1000)
            meta_up = self.config.get('meta_upload', 500)
            testes_ruins = df[df['Download (Mbps)'] < meta_down * 0.8]
            perc_ruim = (len(testes_ruins) / len(df)) * 100
            
            data_primeiro = stats['data_primeiro'].strftime('%d/%m/%Y %H:%M')
            data_ultimo = stats['data_ultimo'].strftime('%d/%m/%Y %H:%M')
            
            # Monta relatório
            relatorio = f"""═══════════════════════════════════════════════════
   RELATÓRIO DE MONITORAMENTO DE INTERNET
═══════════════════════════════════════════════════

Período: {data_primeiro} até {data_ultimo}
Total de Testes: {stats['total_testes']}
Meta Contratada: {meta_down} Mbps Down / {meta_up} Mbps Up

--- DOWNLOAD ---
Média: {stats['down_mean']:.2f} Mbps
Desvio Padrão: {stats['down_std']:.2f} Mbps
Mínimo: {stats['down_min']:.2f} Mbps
Máximo: {stats['down_max']:.2f} Mbps
Desempenho: {(stats['down_mean']/meta_down)*100:.1f}% da meta

--- UPLOAD ---
Média: {stats['up_mean']:.2f} Mbps
Mínimo: {stats['up_min']:.2f} Mbps
Máximo: {stats['up_max']:.2f} Mbps
Desempenho: {(stats['up_mean']/meta_up)*100:.1f}% da meta

--- LATÊNCIA (PING) ---
Média: {stats['ping_mean']:.2f} ms
Mínimo: {stats['ping_min']:.2f} ms
Máximo: {stats['ping_max']:.2f} ms

--- QUALIDADE ---
Testes abaixo de 80% da meta: {len(testes_ruins)} ({perc_ruim:.1f}%)

═══════════════════════════════════════════════════
"""
            
            # Salva relatório em arquivo
            nome_relatorio = os.path.join(self.pasta_script, f"relatorio_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(nome_relatorio, 'w', encoding='utf-8') as f:
                f.write(relatorio)
            
            # Abre o relatório
            messagebox.showinfo("Relatório Gerado", f"Relatório salvo em:\n{nome_relatorio}")
            subprocess.Popen(f'notepad "{nome_relatorio}"')
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar relatório: {e}")
    
    def abrir_configuracoes(self):
        """
        Abre janela de diálogo para editar configurações.
        
        Permite editar:
        - Metas de download/upload/ping (para indicadores visuais)
        - Intervalo de testes automáticos
        - Quantidade de testes exibidos no gráfico
        - Servidores de ping e quantidade de pacotes
        
        Salva diretamente em config.json ao clicar "Salvar".
        """
        config_window = tk.Toplevel(self.root)
        config_window.title("Configurações")
        config_window.geometry("450x400")
        config_window.configure(bg="#f0f0f0")
        config_window.transient(self.root)  # Janela modal
        config_window.grab_set()            # Bloqueia interação com janela principal
        
        # Frame principal
        main_frame = ttk.Frame(config_window, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text="⚙️ Configurações do Monitor", 
                 font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))
        
        # Entradas de configuração (campos editáveis)
        configs = []  # Lista para armazenar (chave, var, tipo) de cada campo
        
        def criar_campo(label, chave, tipo=float):
            """Helper: cria um campo de entrada com label e valor do config.json"""
            frame = ttk.Frame(main_frame)
            frame.pack(fill="x", pady=5)
            ttk.Label(frame, text=label, width=25).pack(side="left")
            var = tk.StringVar(value=str(self.config.get(chave)))  # Carrega valor atual
            entry = ttk.Entry(frame, textvariable=var, width=15)
            entry.pack(side="left", padx=10)
            configs.append((chave, var, tipo))  # Salva para processar depois
            return var
        
        # Campos de configuração
        criar_campo("Meta Download (Mbps):", "meta_download", int)
        criar_campo("Meta Upload (Mbps):", "meta_upload", int)
        criar_campo("Meta Ping (ms):", "meta_ping", int)
        criar_campo("Intervalo Auto-Teste (min):", "intervalo_auto_teste", int)
        criar_campo("Gráfico: Últimos N testes:", "grafico_ultimos_n", int)
        criar_campo("Ping: Quantidade de pacotes:", "ping_count", int)
        
        # Área de servidores de ping
        ttk.Label(main_frame, text="\nServidores de Ping (um por linha):", 
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 5))
        
        ping_text = tk.Text(main_frame, height=6, width=40)
        ping_text.pack(fill="x", pady=5)
        ping_targets = self.config.get('ping_targets', [])
        ping_text.insert("1.0", "\n".join(ping_targets))
        
        # Botões
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        
        def salvar():
            """Callback do botão Salvar - valida e persiste configurações"""
            try:
                # Salva campos numéricos (converte string -> int/float)
                for chave, var, tipo in configs:
                    valor = tipo(var.get())
                    self.config.atualizar(chave, valor)
                
                # Salva lista de servidores de ping (Text widget com múltiplas linhas)
                ping_lines = ping_text.get("1.0", "end").strip().split("\n")
                ping_list = [line.strip() for line in ping_lines if line.strip()]  # Remove linhas vazias
                self.config.atualizar('ping_targets', ping_list)
                
                messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!", parent=config_window)
                
                # Atualiza gráfico se necessário
                self.atualizar_grafico_embedded()
                config_window.destroy()
            except ValueError:
                messagebox.showerror("Erro", "Por favor, insira valores numéricos válidos.", parent=config_window)
        
        tk.Button(btn_frame, text="💾 Salvar", command=salvar, 
                 bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"),
                 relief="flat", padx=20, pady=5, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="❌ Cancelar", command=config_window.destroy,
                 bg="#f44336", fg="white", font=("Segoe UI", 10),
                 relief="flat", padx=20, pady=5, cursor="hand2").pack(side="left", padx=5)
    
    def abrir_pasta(self):
        """Abre o diretório do script no Windows Explorer (para acessar logs/config)"""
        subprocess.Popen(f'explorer "{self.pasta_script}"')


# ============================================================================
# PONTO DE ENTRADA DO APLICATIVO
# ============================================================================
if __name__ == "__main__":
    # Inicializa Tkinter
    root = tk.Tk()
    
    # Cria instância do aplicativo (inicializa toda a UI e componentes)
    app = MonitorInternetApp(root)
    
    # Inicia loop de eventos do Tkinter (fica rodando até fechar a janela)
    root.mainloop()