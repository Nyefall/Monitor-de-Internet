import os
import speedtest
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
META_DOWNLOAD = 1000  # Mbps
LIMITE_HARDWARE = 100 # Mbps
NOME_ARQUIVO_CSV = 'monitoramento_internet.csv'

class MonitorInternetApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor Peganet 1000M")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f0f0")

        # Caminhos
        self.pasta_script = os.path.dirname(os.path.abspath(__file__))
        self.arquivo_csv = os.path.join(self.pasta_script, NOME_ARQUIVO_CSV)

        self.setup_ui()
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
        self.lbl_client_info.pack(fill="x", pady=(0, 10))

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
        
        self.btn_testar = tk.Button(btn_frame, text="INICIAR TESTE COMPLETO", command=self.iniciar_teste, 
                                    bg="#4CAF50", fg="white", font=("Segoe UI", 11, "bold"), 
                                    relief="flat", padx=20, pady=10, cursor="hand2")
        self.btn_testar.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_pasta = tk.Button(btn_frame, text="📂 Abrir Logs", command=self.abrir_pasta, 
                                   bg="#2196F3", fg="white", font=("Segoe UI", 10), 
                                   relief="flat", padx=15, cursor="hand2")
        self.btn_pasta.pack(side="right", padx=(5, 0))

        # Área do Gráfico
        self.graph_frame = ttk.Frame(main_frame)
        self.graph_frame.pack(fill="both", expand=True)
        
        # Placeholder para o gráfico
        self.lbl_no_data = ttk.Label(self.graph_frame, text="Nenhum dado histórico disponível.", font=("Segoe UI", 12))
        self.lbl_no_data.pack(expand=True)

    def criar_card(self, parent, titulo, icone, col):
        frame = tk.Frame(parent, bg="white", bd=1, relief="solid")
        frame.grid(row=0, column=col, padx=5, sticky="ew")
        
        tk.Label(frame, text=f"{icone} {titulo}", bg="white", fg="#666", font=("Segoe UI", 10)).pack(pady=(10, 0))
        lbl_valor = tk.Label(frame, text="--", bg="white", fg="#333", font=("Segoe UI", 16, "bold"))
        lbl_valor.pack(pady=(5, 10))
        
        return lbl_valor

    def verificar_csv(self):
        pass

    def iniciar_teste(self):
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
        self.progress.stop()
        self.btn_testar.config(state="normal", text="INICIAR TESTE COMPLETO", bg="#4CAF50")

        if sucesso:
            self.lbl_status.config(text=f"Último Teste: {data_hora}", foreground="green")
            self.lbl_client_info.config(text=f"Provedor: {isp} | IP: {ip}")
            
            self.card_down.config(text=f"{down:.1f} Mbps")
            self.card_up.config(text=f"{up:.1f} Mbps")
            self.card_ping.config(text=f"{ping:.0f} ms")
            
            loss_text = f"{packet_loss}%" if packet_loss >= 0 else "Erro"
            loss_color = "red" if packet_loss > 0 else "#333"
            self.card_loss.config(text=loss_text, fg=loss_color)
            
            self.atualizar_grafico_embedded()
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
            df = pd.read_csv(self.arquivo_csv, delimiter=';', decimal=',')
            if df.empty:
                return
                
            df['Data e Hora'] = pd.to_datetime(df['Data e Hora'], format='%d/%m/%Y %H:%M:%S')
            
            # Pega apenas os últimos 20 registros para não poluir
            df = df.tail(20)

            # Cria a figura do Matplotlib
            fig = plt.Figure(figsize=(6, 4), dpi=100)
            ax = fig.add_subplot(111)
            
            ax.plot(df['Data e Hora'], df['Download (Mbps)'], label='Download', color='#2196F3', marker='o', linewidth=2)
            ax.plot(df['Data e Hora'], df['Upload (Mbps)'], label='Upload', color='#FF9800', marker='x', linestyle='--')

            ax.axhline(y=META_DOWNLOAD, color='r', linestyle=':', alpha=0.5, label='Meta')
            
            ax.set_title('Histórico Recente (Últimos 20 testes)', fontsize=10)
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

    def gerar_grafico(self):
        # Mantido apenas se quiser abrir em janela separada (opcional), mas agora usamos o embedded
        pass

    def abrir_pasta(self):
        subprocess.Popen(f'explorer "{self.pasta_script}"')

if __name__ == "__main__":
    root = tk.Tk()
    app = MonitorInternetApp(root)
    root.mainloop()