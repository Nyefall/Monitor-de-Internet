import os
import csv
import datetime
import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import re
import json
import sys

# --- CONFIGURAÇÕES ---
META_DOWNLOAD = 1000  # Mbps (meta contratada)
META_UPLOAD = 500  # Mbps (meta contratada)
META_PING = 20  # ms (latência aceitável)
NOME_ARQUIVO_CSV = 'monitoramento_internet.csv'
INTERVALO_AUTO_TESTE = 30  # minutos entre testes automáticos

class MonitorInternetApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor Internet")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f0f0")

        # Caminhos
        self.pasta_script = os.path.dirname(os.path.abspath(__file__))
        self.arquivo_csv = os.path.join(self.pasta_script, NOME_ARQUIVO_CSV)
        
        # Cache e controle
        self.df_cache = None
        self.cache_timestamp = 0
        self.auto_teste_ativo = False
        self.auto_teste_job = None
        self.testando = False

        self.setup_ui()
        self.carregar_ultimo_teste()
        self.atualizar_grafico_embedded()

    def setup_ui(self):
        # Estilo
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

        # Cards de Status (Grid Layout)
        cards_frame = ttk.Frame(main_frame)
        cards_frame.pack(fill="x", pady=(0, 20))
        cards_frame.columnconfigure(0, weight=1)
        cards_frame.columnconfigure(1, weight=1)
        cards_frame.columnconfigure(2, weight=1)
        cards_frame.columnconfigure(3, weight=1)

        # Card Download
        self.card_down = self.criar_card(cards_frame, "Download", "⬇️", 0)
        # Card Upload
        self.card_up = self.criar_card(cards_frame, "Upload", "⬆️", 1)
        # Card Ping
        self.card_ping = self.criar_card(cards_frame, "Ping", "📶", 2)
        # Card Perda de Pacotes
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
        try:
            self.root.after(0, lambda: self.lbl_status.config(text="Executando Speedtest (pode demorar)..."))
            
            # Executa o speedtest como subprocesso para evitar erros de biblioteca (403 Forbidden)
            # Usa o mesmo interpretador Python atual
            cmd = [sys.executable, '-m', 'speedtest', '--secure', '--json']
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            processo = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                      startupinfo=startupinfo, text=True)
            
            stdout, stderr = processo.communicate()
            
            if processo.returncode != 0:
                raise Exception(f"Erro CLI: {stderr}")

            resultado = json.loads(stdout)
            
            down = resultado['download'] / 1_000_000
            up = resultado['upload'] / 1_000_000
            ping = resultado['ping']
            client = resultado['client']
            isp = client.get('isp', 'Desconhecido')
            ip = client.get('ip', 'Desconhecido')
            
            self.root.after(0, lambda: self.lbl_status.config(text="Medindo Perda de Pacotes..."))
            packet_loss = self.medir_perda_pacotes()
            
            data_hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            sucesso, msg = self.salvar_csv(data_hora, down, up, ping, packet_loss, isp, ip)
            self.root.after(0, lambda: self.finalizar_teste(sucesso, msg, data_hora, down, up, ping, packet_loss, isp, ip))

        except Exception as e:
            error_message = str(e)
            if "403" in error_message:
                error_message = "Erro 403: Falha na API do Speedtest. Tente atualizar a biblioteca: 'pip install speedtest-cli --upgrade'"
            self.root.after(0, lambda: self.finalizar_teste(False, error_message))

    def salvar_csv(self, data_hora, down, up, ping, packet_loss, isp, ip):
        novo_arquivo = not os.path.exists(self.arquivo_csv)
        colunas = ["Data e Hora", "Download (Mbps)", "Upload (Mbps)", "Ping (ms)", "Perda Pacotes (%)", "Provedor", "IP Cliente"]
        
        try:
            # Se o arquivo já existe, verifica se precisa atualizar o cabeçalho (migração)
            if not novo_arquivo:
                with open(self.arquivo_csv, 'r', encoding='utf-8-sig') as f:
                    cabecalho_atual = f.readline().strip().split(';')
                
                if len(cabecalho_atual) < len(colunas):
                    # Lê todo o conteúdo antigo
                    df_antigo = pd.read_csv(self.arquivo_csv, delimiter=';', decimal=',')
                    # Adiciona colunas faltantes
                    for col in colunas:
                        if col not in df_antigo.columns:
                            df_antigo[col] = "N/A"
                    # Salva novamente com o novo formato
                    df_antigo.to_csv(self.arquivo_csv, sep=';', decimal=',', index=False, encoding='utf-8-sig')

            with open(self.arquivo_csv, mode='a', newline='', encoding='utf-8-sig') as f:
                escritor = csv.writer(f, delimiter=';')
                if novo_arquivo:
                    escritor.writerow(colunas)
                
                escritor.writerow([
                    data_hora, 
                    f"{down:.2f}".replace('.', ','), 
                    f"{up:.2f}".replace('.', ','), 
                    f"{ping:.2f}".replace('.', ','),
                    f"{packet_loss}",
                    isp,
                    ip
                ])
            return True, "Sucesso"
        except PermissionError:
            return False, "O arquivo Excel está aberto. Feche-o e tente novamente."
        except Exception as e:
            return False, str(e)

    def finalizar_teste(self, sucesso, msg, data_hora=None, down=0, up=0, ping=0, packet_loss=0, isp="--", ip="--"):
        self.testando = False
        self.progress.stop()
        self.btn_testar.config(state="normal", text="INICIAR TESTE", bg="#4CAF50")

        if sucesso:
            self.lbl_status.config(text=f"Último Teste: {data_hora}", foreground="green")
            self.lbl_client_info.config(text=f"Provedor: {isp} | IP: {ip}")
            
            # Atualiza cards com indicadores visuais de qualidade
            self.atualizar_card_com_cor(self.card_down, down, META_DOWNLOAD, f"{down:.1f} Mbps", maior_melhor=True)
            self.atualizar_card_com_cor(self.card_up, up, META_UPLOAD, f"{up:.1f} Mbps", maior_melhor=True)
            self.atualizar_card_com_cor(self.card_ping, ping, META_PING, f"{ping:.0f} ms", maior_melhor=False)
            
            loss_text = f"{packet_loss}%" if packet_loss >= 0 else "Erro"
            loss_color = "red" if packet_loss > 0 else "#333"
            self.card_loss.config(text=loss_text, fg=loss_color)
            
            # Invalida cache e atualiza
            self.df_cache = None
            self.atualizar_grafico_embedded()
            self.atualizar_estatisticas()
        else:
            self.lbl_status.config(text="Erro no teste", foreground="red")
            messagebox.showerror("Erro", f"Falha: {msg}")

    def atualizar_grafico_embedded(self):
        # Limpa a área do gráfico
        for widget in self.graph_frame.winfo_children():
            widget.destroy()

        if not os.path.exists(self.arquivo_csv):
            ttk.Label(self.graph_frame, text="Execute um teste para ver o histórico.", font=("Segoe UI", 12)).pack(expand=True)
            return

        try:
            df = self.carregar_dados_cache()
            if df is None or df.empty:
                ttk.Label(self.graph_frame, text="Nenhum dado disponível.", font=("Segoe UI", 12)).pack(expand=True)
                return
            
            # Pega apenas os últimos 30 registros para melhor visualização
            df_plot = df.tail(30).copy()

            # Cria a figura do Matplotlib
            fig = plt.Figure(figsize=(6, 4), dpi=100)
            ax = fig.add_subplot(111)
            
            ax.plot(df_plot['Data e Hora'], df_plot['Download (Mbps)'], label='Download', color='#2196F3', marker='o', linewidth=2, markersize=4)
            ax.plot(df_plot['Data e Hora'], df_plot['Upload (Mbps)'], label='Upload', color='#FF9800', marker='x', linestyle='--', linewidth=1.5, markersize=5)

            ax.axhline(y=META_DOWNLOAD, color='r', linestyle=':', alpha=0.5, label=f'Meta Down ({META_DOWNLOAD})')
            ax.axhline(y=META_UPLOAD, color='orange', linestyle=':', alpha=0.3, label=f'Meta Up ({META_UPLOAD})')
            
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

    def carregar_dados_cache(self):
        """Carrega dados do CSV com cache para melhor performance"""
        try:
            # Verifica se precisa recarregar (arquivo modificado)
            arquivo_mtime = os.path.getmtime(self.arquivo_csv)
            if self.df_cache is not None and arquivo_mtime == self.cache_timestamp:
                return self.df_cache
            
            # Carrega e processa dados
            df = pd.read_csv(self.arquivo_csv, delimiter=';', decimal=',')
            if not df.empty:
                df['Data e Hora'] = pd.to_datetime(df['Data e Hora'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
                df = df.dropna(subset=['Data e Hora'])  # Remove linhas com data inválida
                
                self.df_cache = df
                self.cache_timestamp = arquivo_mtime
            return df
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
            return None
    
    def carregar_ultimo_teste(self):
        """Carrega e exibe dados do último teste realizado"""
        try:
            df = self.carregar_dados_cache()
            if df is not None and not df.empty:
                ultimo = df.iloc[-1]
                self.lbl_client_info.config(text=f"Provedor: {ultimo.get('Provedor', '--')} | IP: {ultimo.get('IP Cliente', '--')}")
                self.atualizar_estatisticas()
        except Exception as e:
            print(f"Erro ao carregar último teste: {e}")
    
    def atualizar_card_com_cor(self, card_label, valor, meta, texto, maior_melhor=True):
        """Atualiza card com cores baseadas na performance"""
        card_label.config(text=texto)
        
        # Calcula performance relativa
        if maior_melhor:
            performance = (valor / meta) if meta > 0 else 0
            cor_fundo = "#C8E6C9" if performance >= 0.8 else "#FFECB3" if performance >= 0.5 else "#FFCDD2"
        else:  # Para ping, menor é melhor
            performance = (meta / valor) if valor > 0 else 0
            cor_fundo = "#C8E6C9" if performance >= 0.8 else "#FFECB3" if performance >= 0.5 else "#FFCDD2"
        
        # Atualiza cor de fundo do frame pai
        parent_frame = card_label.master
        parent_frame.config(bg=cor_fundo)
        if hasattr(parent_frame, 'lbl_titulo'):
            parent_frame.lbl_titulo.config(bg=cor_fundo)
        card_label.config(bg=cor_fundo)
    
    def atualizar_estatisticas(self):
        """Calcula e exibe estatísticas dos últimos testes"""
        try:
            df = self.carregar_dados_cache()
            if df is None or df.empty:
                self.lbl_stats.config(text="Sem dados para estatísticas")
                return
            
            # Últimos 10 testes
            df_recente = df.tail(10)
            
            down_mean = df_recente['Download (Mbps)'].mean()
            down_min = df_recente['Download (Mbps)'].min()
            down_max = df_recente['Download (Mbps)'].max()
            
            ping_mean = df_recente['Ping (ms)'].mean()
            
            total_testes = len(df)
            
            texto_stats = f"📈 Últimos 10 testes - Download: Média {down_mean:.1f} | Min {down_min:.1f} | Max {down_max:.1f} Mbps | Ping Médio: {ping_mean:.0f}ms | Total de testes: {total_testes}"
            self.lbl_stats.config(text=texto_stats)
        except Exception as e:
            self.lbl_stats.config(text=f"Erro ao calcular estatísticas: {e}")
    
    def toggle_auto_teste(self):
        """Ativa/desativa testes automáticos periódicos"""
        self.auto_teste_ativo = not self.auto_teste_ativo
        
        if self.auto_teste_ativo:
            self.btn_auto.config(text="🔄 Auto (ON)", bg="#4CAF50")
            self.lbl_status.config(text=f"Teste automático ativo (a cada {INTERVALO_AUTO_TESTE}min)", foreground="blue")
            self.agendar_proximo_teste()
        else:
            self.btn_auto.config(text="🔄 Auto (OFF)", bg="#9E9E9E")
            if self.auto_teste_job:
                self.root.after_cancel(self.auto_teste_job)
                self.auto_teste_job = None
            self.lbl_status.config(text="Teste automático desativado", foreground="gray")
    
    def agendar_proximo_teste(self):
        """Agenda o próximo teste automático"""
        if self.auto_teste_ativo:
            intervalo_ms = INTERVALO_AUTO_TESTE * 60 * 1000  # Converte minutos para milissegundos
            self.auto_teste_job = self.root.after(intervalo_ms, self.executar_teste_automatico)
    
    def executar_teste_automatico(self):
        """Executa um teste automático"""
        if not self.testando:
            self.iniciar_teste()
        self.agendar_proximo_teste()
    
    def gerar_relatorio(self):
        """Gera um relatório em texto com análise dos dados"""
        try:
            df = self.carregar_dados_cache()
            if df is None or df.empty:
                messagebox.showinfo("Relatório", "Nenhum dado disponível para gerar relatório.")
                return
            
            # Análise estatística
            down_mean = df['Download (Mbps)'].mean()
            down_std = df['Download (Mbps)'].std()
            down_min = df['Download (Mbps)'].min()
            down_max = df['Download (Mbps)'].max()
            
            up_mean = df['Upload (Mbps)'].mean()
            up_min = df['Upload (Mbps)'].min()
            up_max = df['Upload (Mbps)'].max()
            
            ping_mean = df['Ping (ms)'].mean()
            ping_min = df['Ping (ms)'].min()
            ping_max = df['Ping (ms)'].max()
            
            # Testes abaixo da meta
            testes_ruins = df[df['Download (Mbps)'] < META_DOWNLOAD * 0.8]
            perc_ruim = (len(testes_ruins) / len(df)) * 100
            
            data_primeiro = df.iloc[0]['Data e Hora'].strftime('%d/%m/%Y %H:%M')
            data_ultimo = df.iloc[-1]['Data e Hora'].strftime('%d/%m/%Y %H:%M')
            
            # Monta relatório
            relatorio = f"""═══════════════════════════════════════════════════
   RELATÓRIO DE MONITORAMENTO DE INTERNET
═══════════════════════════════════════════════════

Período: {data_primeiro} até {data_ultimo}
Total de Testes: {len(df)}
Meta Contratada: {META_DOWNLOAD} Mbps Down / {META_UPLOAD} Mbps Up

--- DOWNLOAD ---
Média: {down_mean:.2f} Mbps
Desvio Padrão: {down_std:.2f} Mbps
Mínimo: {down_min:.2f} Mbps
Máximo: {down_max:.2f} Mbps
Desempenho: {(down_mean/META_DOWNLOAD)*100:.1f}% da meta

--- UPLOAD ---
Média: {up_mean:.2f} Mbps
Mínimo: {up_min:.2f} Mbps
Máximo: {up_max:.2f} Mbps
Desempenho: {(up_mean/META_UPLOAD)*100:.1f}% da meta

--- LATÊNCIA (PING) ---
Média: {ping_mean:.2f} ms
Mínimo: {ping_min:.2f} ms
Máximo: {ping_max:.2f} ms

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
    
    def abrir_pasta(self):
        subprocess.Popen(f'explorer "{self.pasta_script}"')

if __name__ == "__main__":
    root = tk.Tk()
    app = MonitorInternetApp(root)
    root.mainloop()