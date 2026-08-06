import sys
import subprocess
import json
import os
import re
import winreg
import socket
import threading
import webbrowser
import math
import time
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image
import pygetwindow as gw
import pyautogui

CACHE_FILE = "config_cache.json"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def carregar_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def salvar_cache(dados):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Erro ao salvar cache: {e}")

def obter_nome_adaptador(valor):
    valor = str(valor).strip()
    if valor in ["1", "Wi-Fi"]:
        return "Wi-Fi"
    elif valor in ["2", "Ethernet", "Cabo"]:
        return "Ethernet"
    return valor

def executar_ps(comando):
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", comando],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )

def detectar_rede_automatica_cmd():
    adaptador_codigo = "Cabo"
    ip_atual = ""
    gw_atual = ""

    try:
        res = subprocess.run(
            ["ipconfig"],
            capture_output=True,
            text=True,
            encoding="cp850",
            errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        output = res.stdout
        blocos = output.split("\n\n")

        for bloco in blocos:
            linhas = [l.strip() for l in bloco.splitlines() if l.strip()]
            if not linhas:
                continue

            nome_bloco = linhas[0].lower()

            if any(term in nome_bloco for term in ["mídia desconectada", "media disconnected", "vbox", "vmware", "wsl", "vethernet", "bluetooth", "loopback"]):
                continue

            ip_temp = ""
            gw_temp = ""

            for linha in linhas:
                if "IPv4" in linha:
                    match_ip = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', linha)
                    if match_ip:
                        ip_val = match_ip.group(1)
                        if not ip_val.startswith("127.") and not ip_val.startswith("169.254."):
                            ip_temp = ip_val

                elif "Gateway Padr" in linha or "Default Gateway" in linha:
                    match_gw = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', linha)
                    if match_gw:
                        gw_val = match_gw.group(1)
                        if gw_val != "0.0.0.0":
                            gw_temp = gw_val

            if ip_temp:
                ip_atual = ip_temp
                octetos_ip = ip_temp.split(".")
                subrede_ip = f"{octetos_ip[0]}.{octetos_ip[1]}.{octetos_ip[2]}"

                if gw_temp and gw_temp.startswith(f"{subrede_ip}."):
                    gw_atual = gw_temp
                else:
                    gw_atual = f"{subrede_ip}.1"

                if any(w in nome_bloco for w in ["wi-fi", "wifi", "wlan", "sem fio", "wireless"]):
                    adaptador_codigo = "Wi-Fi"
                else:
                    adaptador_codigo = "Cabo"
                break

    except Exception as e:
        print(f"Erro ao auto-detectar via CMD: {e}")

    return adaptador_codigo, ip_atual, gw_atual

def ao_digitar_novo_ip(event=None):
    ip_texto = entry_novo_ip.get().strip()
    partes = ip_texto.split(".")
    
    if len(partes) == 4 and all(p.isdigit() for p in partes[:3]):
        gateway_auto = f"{partes[0]}.{partes[1]}.{partes[2]}.1"
        entry_novo_gw.delete(0, "end")
        entry_novo_gw.insert(0, gateway_auto)

def alternar_spoiler():
    global spoiler_aberto
    if spoiler_aberto:
        frame_spoiler.pack_forget()
        btn_spoiler.configure(text="▶ 🛠️ Exibir Configurações Avançadas de Rede")
        spoiler_aberto = False
    else:
        frame_spoiler.pack(fill="x", pady=(0, 10), before=frame_acoes_rede)
        btn_spoiler.configure(text="▼ 🛠️ Ocultar Configurações Avançadas")
        spoiler_aberto = True

def aplicar_config():
    adaptador_raw = seg_adaptador.get()
    adaptador = obter_nome_adaptador(adaptador_raw)
    
    ip_atual = entry_ip_atual.get().strip()
    gw_atual = entry_gw_atual.get().strip()
    novo_ip_digitado = entry_novo_ip.get().strip()
    mascara = entry_mascara.get().strip()
    novo_gw = entry_novo_gw.get().strip()

    if not all([adaptador, ip_atual, gw_atual, novo_ip_digitado, mascara, novo_gw]):
        messagebox.showwarning("Aviso", "Por favor, preencha todos os campos!")
        return

    partes_ip = novo_ip_digitado.split(".")
    if len(partes_ip) == 4 and all(p.isdigit() for p in partes_ip[:3]):
        novo_ip_real = f"{partes_ip[0]}.{partes_ip[1]}.{partes_ip[2]}.254"
    else:
        novo_ip_real = novo_ip_digitado

    dados_para_salvar = {
        "adaptador": adaptador_raw,
        "ip_atual": ip_atual,
        "gw_atual": gw_atual,
        "novo_ip": novo_ip_digitado,
        "mascara": mascara,
        "novo_gw": novo_gw
    }
    salvar_cache(dados_para_salvar)

    try:
        cmd1 = f'netsh interface ipv4 set address name="{adaptador}" static {ip_atual} {mascara} {gw_atual} 1'
        res1 = subprocess.run(cmd1, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if res1.returncode != 0:
            raise Exception(f"Passo 1 (Fixar IP):\n{res1.stderr or res1.stdout}")

        cmd2 = f'netsh interface ipv4 add address name="{adaptador}" {novo_ip_real} {mascara}'
        res2 = subprocess.run(cmd2, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if res2.returncode != 0:
            raise Exception(f"Passo 2 (Adicionar IP):\n{res2.stderr or res2.stdout}")

        cmd3 = f'netsh interface ipv4 add address name="{adaptador}" gateway={novo_gw} gwmetric=2'
        res3 = subprocess.run(cmd3, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if res3.returncode != 0:
            raise Exception(f"Passo 3 (Adicionar Gateway):\n{res3.stderr or res3.stdout}")

        messagebox.showinfo("Sucesso", f"REDE CONFIGURADA COM SUCESSO!\nAdaptador: {adaptador}\nA rede do cliente e a impressora já estão ativas.")

    except Exception as e:
        messagebox.showerror("Erro de Configuração", f"Falha ao aplicar configurações:\n\n{str(e)}")

def restaurar_dhcp():
    adaptador_raw = seg_adaptador.get()
    adaptador = obter_nome_adaptador(adaptador_raw)
    
    if not adaptador:
        messagebox.showwarning("Aviso", "Selecione o Adaptador de Rede para restaurar!")
        return

    try:
        cmd1 = f'netsh interface ipv4 set address name="{adaptador}" source=dhcp'
        subprocess.run(cmd1, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

        cmd2 = f'netsh interface ipv4 set dns name="{adaptador}" source=dhcp'
        subprocess.run(cmd2, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

        messagebox.showinfo("Sucesso", f"Rede do adaptador '{adaptador}' restaurada com sucesso para DHCP automático!")
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao restaurar DHCP:\n{str(e)}")

def reiniciar_spooler():
    try:
        res_stop = subprocess.run(
            ["net", "stop", "spooler"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        res_start = subprocess.run(
            ["net", "start", "spooler"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if res_start.returncode == 0:
            messagebox.showinfo("Sucesso", "Serviço Spooler de Impressão reiniciado com sucesso!")
        else:
            messagebox.showerror("Erro", f"Falha ao iniciar o Spooler:\n{res_start.stderr or res_start.stdout}")
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao reiniciar o Spooler:\n{str(e)}")

def abrir_control_printers():
    try:
        subprocess.Popen("explorer.exe shell:::{A8A91A66-3A7D-4424-8D24-04E180695C7A}")
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao abrir Dispositivos e Impressoras:\n{str(e)}")

# --- FUNÇÃO PARA ORGANIZAR JANELAS EM GRADE ---
def organizar_janelas_grade():
    win_grad = ctk.CTkToplevel(root)
    win_grad.title("Organizar Janelas em Grade")
    win_grad.geometry("450x380")
    win_grad.resizable(False, False)
    win_grad.configure(fg_color="#18191c")

    lbl_t = ctk.CTkLabel(win_grad, text="ORGANIZADOR DE JANELAS EM GRADE", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff")
    lbl_t.pack(pady=(15, 5))

    lbl_desc = ctk.CTkLabel(win_grad, text="Digite os títulos (ou parte deles) das janelas que deseja alinhar,\nseparados por vírgula:", text_color="#949ba4", font=ctk.CTkFont(size=11))
    lbl_desc.pack(pady=(0, 10))

    entry_titulos = ctk.CTkEntry(win_grad, corner_radius=8, fg_color="#2b2d31", border_color="#383a40", text_color="#ffffff", placeholder_text="Ex: Chrome, Bloco de Notas, Visual Studio Code")
    entry_titulos.insert(0, "Chrome, Bloco de Notas, Calculadora")
    entry_titulos.pack(fill="x", padx=20, pady=(0, 15))

    lbl_log = ctk.CTkLabel(win_grad, text="", font=ctk.CTkFont(size=11), text_color="#23a55a")
    lbl_log.pack(pady=5)

    def executar_alinhamento():
        texto = entry_titulos.get().strip()
        if not texto:
            messagebox.showwarning("Aviso", "Informe ao menos um título de janela!", parent=win_grad)
            return

        titulos = [t.strip() for t in texto.split(",") if t.strip()]
        
        largura_tela, altura_tela = pyautogui.size()
        janelas_encontradas = []

        for t in titulos:
            matches = gw.getWindowsWithTitle(t)
            if matches:
                janelas_encontradas.append(matches[0])

        num_janelas = len(janelas_encontradas)
        if num_janelas == 0:
            lbl_log.configure(text="❌ Nenhuma janela correspondente foi encontrada.", text_color="#f23f43")
            return

        colunas = math.ceil(math.sqrt(num_janelas))
        linhas = math.ceil(num_janelas / colunas)

        largura_celula = largura_tela // colunas
        altura_celula = altura_tela // linhas

        for idx, janela in enumerate(janelas_encontradas):
            col = idx % colunas
            lin = idx // colunas

            x = col * largura_celula
            y = lin * altura_celula

            try:
                if janela.isMinimized:
                    janela.restore()
                janela.moveTo(x, y)
                janela.resizeTo(largura_celula, altura_celula)
            except Exception as e:
                print(f"Erro ao mover janela: {e}")

        lbl_log.configure(text=f"✅ {num_janelas} janela(s) organizadas em grade {colunas}x{linhas}!", text_color="#23a55a")

    btn_exec = ctk.CTkButton(win_grad, text="📐 Aplicar Grade Agora", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#23a55a", hover_color="#1d8a4b", height=38, command=executar_alinhamento)
    btn_exec.pack(fill="x", padx=20, pady=(10, 15))

def abrir_janela_drivers():
    win = ctk.CTkToplevel(root)
    win.title("Central de Drivers de Impressoras")
    win.geometry("580x680")
    win.resizable(False, False)
    win.configure(fg_color="#18191c")

    lbl_titulo_drv = ctk.CTkLabel(win, text="DOWNLOADS DE DRIVERS E UTILITÁRIOS", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff")
    lbl_titulo_drv.pack(pady=(15, 10))

    scroll_drv = ctk.CTkScrollableFrame(win, corner_radius=10, fg_color="#1e1f22")
    scroll_drv.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    dados_drivers = {
        "BEMATECH": [
            ("Driver Spooler MP-2500TH ao MP-5100 TH (x64)", "https://drive.google.com/file/d/1P1rTHrXbkayFjcxWNWPYpCs0Sq7f2Le1/view?usp=sharing"),
            ("Driver Spooler MP-2800", "https://drive.google.com/file/d/1Iv5SmbIEOL0lQI2q156KB8fq3YL8obwT/view?usp=sharing"),
            ("Printer Tool MP-2800", "https://drive.google.com/file/d/1HPRxiVQYWpkJSnCUaFwM3DGP52anBvw0/view?usp=sharing"),
            ("Driver MP-4200 HS", "https://github.com/ElginDeveloperCommunity/Impressoras/tree/master/Impressoras%20Não%20Fiscais/Utilitários%20Bematech/MP-4200%20HS/Drivers")
        ],
        "ELGIN": [
            ("Driver i9 Atualizado", "https://github.com/ElginDeveloperCommunity/Impressoras/tree/master/Impressoras%20Não%20Fiscais/Utilitários%20Elgin/i9/Drivers"),
            ("Driver i8", "https://github.com/ElginDeveloperCommunity/Impressoras/tree/master/Impressoras%20Não%20Fiscais/Utilitários%20Elgin/i8/Drivers"),
            ("Driver i7", "https://drive.google.com/file/d/1tjpb4Ygl-hKd3dPlNymN1_2U8_ks4NDz/view?usp=sharing"),
            ("Driver Porta COM i7", "https://drive.google.com/file/d/1ZJlvShP5PRvIjLY6iLzRVrEjBbVklw3j/view?usp=sharing"),
            ("Driver i10", "https://drive.google.com/file/d/1prtqBRxxNS_T-_OoHeEfOwNBp1vcn1Iy/view?usp=sharing"),
            ("Driver L42", "https://drive.google.com/file/d/1r_4eAywBFZh02PUHK8rutKxp7XMES4fd/view?usp=sharing")
        ],
        "EPSON": [
            ("Driver TM T20", "https://drive.google.com/file/d/1HAyR4OL6oSd1yN3b1C_P0MGh1AXP6wzD/view?usp=sharing"),
            ("Driver TM T20X", "https://drive.google.com/file/d/1m7VQaAlsGY-4ugw5HCp2c99-L5Dmskbo/view?usp=sharing"),
            ("Driver TM T88V / TM T88IV", "https://drive.google.com/file/d/1sjDDglu41w5to7D5Vm52fBrnFtoc2wNj/view?usp=sharing"),
            ("Driver TM T81", "https://drive.google.com/drive/folders/1BIX0vwQTVZrf7N3peOKmIK3Q1GvkeUFt?usp=sharing"),
            ("Driver TM-T20X-II", "https://epson.com.br/Suporte/Ponto-de-venda/Impressoras-de-recibos/Epson-TM-T20X-II/s/SPT_C31CL45011?review-filter=Windows+10+64-bit")
        ],
        "POS 58 E POS 80": [
            ("Driver POS 58 / POS 80 Generic", "https://drive.google.com/file/d/1VzY-A28faTAhkJ7rSYtu8sRyrLG9WgC-/view?usp=sharing")
        ],
        "GENÉRICAS E OUTRAS MARCAS": [
            ("Acervo Técnico / Drivers Sweda", "https://sweda.com.br/acervo-tecnico/"),
            ("Sweda SI-300 Network Tool", "https://sweda.com.br/downloads/SI-300_Tool_Ver_2.03.zip"),
            ("Daruma DR700", "https://drive.google.com/file/d/1Eoesq26Krws0Ew4u8O7uMs8Z95rBKki3/view?usp=sharing"),
            ("Daruma DR800", "https://drive.google.com/drive/folders/1g8gbOXrHN_LIyj4s8Rbr3P4YDxw_4rCr?usp=sharing"),
            ("Diebold IM453HU (E Outros)", "https://dieboldnixdorf.com.br/wp-content/uploads/2021/04/82d59195a9e944b737ddd2a6627a2f95.zip"),
            ("Taicon TP500L (LAN)", "https://www.taicon.com.br/wp-content/uploads/2020/downloads/cd-driver-impressora-termica-lan.zip"),
            ("Taicon TA-TP510L", "https://www.taicon.com.br/wp-content/uploads/2020/downloads/driver-tp510L.zip"),
            ("Taicon TP 610L / 610W", "https://www.taicon.com.br/wp-content/uploads/2020/downloads/driverTA-TP610L-TA-TP610W.zip"),
            ("Taicon Downloads (Linha TA-TP)", "https://www.taicon.com.br/downloads/"),
            ("Olivetti PRT100", "https://www.olivetti.com/sites/default/files/products/drivers/toolkit_prt100_enhanced_2.00_03_0.exe"),
            ("XPrinter (Exe Direct)", "https://drive.google.com/file/d/1Eoesq26Krws0Ew4u8O7uMs8Z95rBKki3/view?usp=sharing"),
            ("Tanca TP-650 (Driver & Utility)", "https://www.tanca.com.br/assets/conteudo/drivers/TP-650/Driver_Utilitarios_TP-650.zip"),
            ("Tanca TP-550 (Driver & Utility)", "https://www.tanca.com.br/assets/conteudo/drivers/TP-550/Driver_Utilitarios_TP-550.zip"),
            ("Tanca TP-450 (Driver & Utility)", "https://www.tanca.com.br/assets/conteudo/drivers/TP-450/Driver_Utilitarios_TP-450.zip"),
            ("Tanca TP-620 Utility", "https://www.tanca.com.br/assets/conteudo/drivers/TP-620/PrinterTools_TP620.zip"),
            ("Tanca TP-620+ Driver", "https://www.tanca.com.br/assets/conteudo/drivers/TP-620+/Driver_Windows.zip"),
            ("Tanca Central de Drivers (Geral)", "https://tanca.com.br/drivers.php?cat=19"),
            ("Jetway JP-800 Driver", "http://jetway.com.br/drives/02-impressoras/JP-800/Driver_Jetway_Printer/Windows10/JetwayPrinterDriverJP-800.exe"),
            ("Jetway JP-800 Network Tool", "http://jetway.com.br/drives/02-impressoras/JP-800/Printertool/PrinterTool_JP-800.zip"),
            ("Gertec G250 / G250W Driver", "https://www.gertec.com.br/wp-content/uploads/2022/06/Driver_Spooler_G250-G250W_VCOM-V1.0-1.zip"),
            ("Gertec G250 Network Tool", "https://www.gertec.com.br/wp-content/uploads/2022/06/Utility_G250_G250W.zip"),
            ("PertoPrinter Driver", "https://www.grupodigicon.com.br/perto/wp-content/uploads/sites/3/2018/10/290.05.091-290.05.089-290.05.085-PertoPrinter-Windows.zip"),
            ("WayTec WP-100 (Drivers e Manuais)", "http://suporte.waytec.com.br/drivers/wp-100/"),
            ("GoldenTec (Todos os Modelos)", "https://ibytef01.sharepoint.com/:u:/s/drivers/EQoDcx5ByopMmdtcV7VDlPQBPmrkE0QXkM3hUTXYLvvr0g?e=e1hUyM"),
            ("GoldenTec 710 (POS80)", "https://ibytef01.sharepoint.com/:u:/s/drivers/Ee3pjWHZ11VClAj1ivLoqHMBtB5aNuxVjzYKFN7VTB6zqQ?e=SSzege"),
            ("GSAN GS-JP80-UE(UB)", "https://drive.google.com/drive/folders/1VbWyXVRECnFR4DM3vBwwxFqVF761Cqlx"),
            ("GSAN Central de Drivers", "https://www.gsan.com/Driver-dc498503.html"),
            ("Repositório GitHub (Vários Drivers)", "https://github.com/Estima01/Drivers-de-impressora/tree/main")
        ]
    }

    def criar_spoiler_categoria(parent, titulo, lista_itens):
        frame_categoria = ctk.CTkFrame(parent, fg_color="#2b2d31", corner_radius=8)
        frame_categoria.pack(fill="x", pady=5)

        conteudo_frame = ctk.CTkFrame(frame_categoria, fg_color="#202225", corner_radius=6)
        
        def alternar():
            if conteudo_frame.winfo_ismapped():
                conteudo_frame.pack_forget()
                btn_cat.configure(text=f"▶ {titulo}")
            else:
                conteudo_frame.pack(fill="x", padx=10, pady=(0, 10))
                btn_cat.configure(text=f"▼ {titulo}")

        btn_cat = ctk.CTkButton(
            frame_categoria, 
            text=f"▶ {titulo}", 
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="transparent", 
            text_color="#ffffff",
            anchor="w",
            hover_color="#383a40",
            command=alternar
        )
        btn_cat.pack(fill="x", padx=5, pady=5)

        for nome, url in lista_itens:
            btn_item = ctk.CTkButton(
                conteudo_frame,
                text=f"🔗 {nome}",
                font=ctk.CTkFont(size=11),
                fg_color="#2b2d31",
                hover_color="#3b3d44",
                anchor="w",
                height=32,
                command=lambda link=url: webbrowser.open(link)
            )
            btn_item.pack(fill="x", pady=2, padx=5)

    for marca, itens in dados_drivers.items():
        criar_spoiler_categoria(scroll_drv, marca, itens)

def abrir_janela_ajuste_impressora():
    win = ctk.CTkToplevel(root)
    win.title("Ajuste de IP e Gateway da Impressora")
    win.geometry("450x480")
    win.resizable(False, False)
    win.configure(fg_color="#18191c")

    lbl_titulo = ctk.CTkLabel(win, text="DIAGNOSTICAR & APLICAR NOVO IP NA IMPRESSORA", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff")
    lbl_titulo.pack(pady=(15, 10))

    frame_corpo = ctk.CTkFrame(win, corner_radius=10, fg_color="#202225")
    frame_corpo.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    lbl_ip_busca = ctk.CTkLabel(frame_corpo, text="IP Atual da Impressora:", text_color="#dcddde", anchor="w")
    lbl_ip_busca.pack(fill="x", padx=15, pady=(10, 2))

    entry_ip_busca = ctk.CTkEntry(frame_corpo, corner_radius=8, fg_color="#2b2d31", border_color="#383a40", text_color="#ffffff", placeholder_text="Ex: 192.168.10.50")
    entry_ip_busca.insert(0, entry_novo_ip.get().strip())
    entry_ip_busca.pack(fill="x", padx=15, pady=(0, 10))

    lbl_status = ctk.CTkLabel(frame_corpo, text="Status: Aguardando verificação...", font=ctk.CTkFont(size=11), text_color="#949ba4")
    lbl_status.pack(pady=5)

    frame_novos_dados = ctk.CTkFrame(frame_corpo, fg_color="transparent")

    lbl_novo_ip_imp = ctk.CTkLabel(frame_novos_dados, text="Novo IPv4 para Impressora:", text_color="#dcddde", anchor="w")
    lbl_novo_ip_imp.pack(fill="x", pady=(5, 2))
    entry_novo_ip_imp = ctk.CTkEntry(frame_novos_dados, corner_radius=8, fg_color="#2b2d31", border_color="#383a40", text_color="#ffffff")
    entry_novo_ip_imp.pack(fill="x", pady=(0, 10))

    lbl_novo_gw_imp = ctk.CTkLabel(frame_novos_dados, text="Novo Gateway da Impressora:", text_color="#dcddde", anchor="w")
    lbl_novo_gw_imp.pack(fill="x", pady=(0, 2))
    entry_novo_gw_imp = ctk.CTkEntry(frame_novos_dados, corner_radius=8, fg_color="#2b2d31", border_color="#383a40", text_color="#ffffff")
    entry_novo_gw_imp.pack(fill="x", pady=(0, 10))

    def abrir_web_panel(ip):
        webbrowser.open(f"http://{ip}")

    def testar_conexao_impressora():
        ip = entry_ip_busca.get().strip()
        if not ip:
            messagebox.showwarning("Aviso", "Digite um IP para testar!", parent=win)
            return

        lbl_status.configure(text="🔍 Verificando comunicação...", text_color="#f0b232")
        win.update()

        res_ping = subprocess.run(["ping", "-n", "1", "-w", "1000", ip], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        ping_ok = res_ping.returncode == 0

        porta_ok = False
        for porta in [9100, 80, 443]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                if s.connect_ex((ip, porta)) == 0:
                    porta_ok = True
                    s.close()
                    break
                s.close()
            except:
                pass

        if ping_ok or porta_ok:
            lbl_status.configure(text=f"✅ Impressora Localizada no IP {ip}!", text_color="#23a55a")
            frame_novos_dados.pack(fill="x", padx=15, pady=5)
            
            partes = ip.split(".")
            if len(partes) == 4:
                entry_novo_gw_imp.delete(0, "end")
                entry_novo_gw_imp.insert(0, f"{partes[0]}.{partes[1]}.{partes[2]}.1")
                entry_novo_ip_imp.delete(0, "end")
                entry_novo_ip_imp.insert(0, ip)

            btn_web.pack(fill="x", padx=15, pady=(5, 10))
        else:
            lbl_status.configure(text=f"❌ Nenhuma impressora respondeu no IP {ip}", text_color="#f23f43")
            frame_novos_dados.pack_forget()
            btn_web.pack_forget()

    btn_verificar = ctk.CTkButton(frame_corpo, text="🔍 Buscar e Testar IP", fg_color="#2b2d31", hover_color="#3b3d44", command=testar_conexao_impressora)
    btn_verificar.pack(fill="x", padx=15, pady=(5, 10))

    btn_web = ctk.CTkButton(
        frame_corpo, 
        text="🌐 Abrir Painel Web (EWS)", 
        fg_color="#23a55a", 
        hover_color="#1d8a4b", 
        command=lambda: abrir_web_panel(entry_ip_busca.get().strip())
    )

def obter_drivers_instalados():
    try:
        res = executar_ps("Get-PrinterDriver | Select-Object -ExpandProperty Name")
        drivers = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        return sorted(drivers) if drivers else ["Generic / Text Only"]
    except Exception:
        return ["Generic / Text Only"]

def obter_portas_instaladas():
    try:
        res = executar_ps("Get-PrinterPort | Select-Object -ExpandProperty Name")
        portas = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        return sorted(portas) if portas else ["LPT1:", "USB001", "COM1:"]
    except Exception:
        return ["LPT1:", "USB001", "COM1:"]

def abrir_janela_criar_dispositivo():
    win = ctk.CTkToplevel(root)
    win.title("Criar Dispositivo e Gerenciar Portas")
    win.geometry("500x580")
    win.resizable(False, False)
    win.configure(fg_color="#18191c")

    scroll = ctk.CTkScrollableFrame(win, corner_radius=10, fg_color="#1e1f22")
    scroll.pack(fill="both", expand=True, padx=12, pady=12)

    lbl_sec1 = ctk.CTkLabel(scroll, text="1. CADASTRAR NOVA PORTA (TCP/IP OU LOCAL)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff")
    lbl_sec1.pack(anchor="w", pady=(5, 10))

    frame_porta = ctk.CTkFrame(scroll, fg_color="#2b2d31", corner_radius=8)
    frame_porta.pack(fill="x", pady=(0, 15))

    lbl_nome_porta = ctk.CTkLabel(frame_porta, text="Nome da Porta ou IP (Ex: 192.168.10.50 ou USB002):", text_color="#dcddde", anchor="w")
    lbl_nome_porta.pack(fill="x", padx=10, pady=(10, 2))
    
    entry_nome_porta = ctk.CTkEntry(frame_porta, corner_radius=8, fg_color="#1e1f22", border_color="#383a40", text_color="#ffffff")
    entry_nome_porta.insert(0, entry_novo_ip.get().strip())
    entry_nome_porta.pack(fill="x", padx=10, pady=(0, 10))

    tipo_porta_var = ctk.StringVar(value="TCP/IP (Rede)")
    rb_tcp = ctk.CTkRadioButton(frame_porta, text="Porta TCP/IP (Standard RAW 9100)", variable=tipo_porta_var, value="TCP/IP (Rede)", text_color="#dcddde")
    rb_tcp.pack(anchor="w", padx=10, pady=2)
    
    rb_local = ctk.CTkRadioButton(frame_porta, text="Porta Local / USB Personalizada", variable=tipo_porta_var, value="Local", text_color="#dcddde")
    rb_local.pack(anchor="w", padx=10, pady=(0, 10))

    def acao_criar_porta():
        val = entry_nome_porta.get().strip()
        tipo = tipo_porta_var.get()

        if not val:
            messagebox.showwarning("Aviso", "Informe o nome ou IP da porta!", parent=win)
            return

        try:
            if tipo == "TCP/IP (Rede)":
                cmd = f"Add-PrinterPort -Name '{val}' -PrinterHostAddress '{val}' -ErrorAction Stop"
            else:
                cmd = f"Add-PrinterPort -Name '{val}' -ErrorAction Stop"

            res = executar_ps(cmd)
            if res.returncode == 0:
                messagebox.showinfo("Sucesso", f"Porta '{val}' criada com sucesso!", parent=win)
                atualizar_combos()
            else:
                messagebox.showerror("Erro", f"Falha ao criar porta:\n{res.stderr or res.stdout}", parent=win)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro na execução:\n{str(e)}", parent=win)

    btn_add_porta = ctk.CTkButton(frame_porta, text="➕ Cadastrar Porta", fg_color="#383a40", hover_color="#4e5058", command=acao_criar_porta)
    btn_add_porta.pack(fill="x", padx=10, pady=(5, 10))

    lbl_sec2 = ctk.CTkLabel(scroll, text="2. CRIAR DISPOSITIVO E VINCULAR DRIVER", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff")
    lbl_sec2.pack(anchor="w", pady=(5, 10))

    frame_disp = ctk.CTkFrame(scroll, fg_color="#2b2d31", corner_radius=8)
    frame_disp.pack(fill="x", pady=(0, 10))

    lbl_nome_disp = ctk.CTkLabel(frame_disp, text="Nome da Impressora/Dispositivo:", text_color="#dcddde", anchor="w")
    lbl_nome_disp.pack(fill="x", padx=10, pady=(10, 2))
    entry_nome_disp = ctk.CTkEntry(frame_disp, corner_radius=8, fg_color="#1e1f22", border_color="#383a40", text_color="#ffffff", placeholder_text="Ex: Impressora Termica Caixas")
    entry_nome_disp.pack(fill="x", padx=10, pady=(0, 10))

    lbl_sel_driver = ctk.CTkLabel(frame_disp, text="Selecione o Driver Instalado:", text_color="#dcddde", anchor="w")
    lbl_sel_driver.pack(fill="x", padx=10, pady=(0, 2))
    combo_driver = ctk.CTkOptionMenu(frame_disp, fg_color="#1e1f22", button_color="#383a40", text_color="#ffffff")
    combo_driver.pack(fill="x", padx=10, pady=(0, 10))

    lbl_sel_porta = ctk.CTkLabel(frame_disp, text="Selecione a Porta de Saída:", text_color="#dcddde", anchor="w")
    lbl_sel_porta.pack(fill="x", padx=10, pady=(0, 2))
    combo_porta = ctk.CTkOptionMenu(frame_disp, fg_color="#1e1f22", button_color="#383a40", text_color="#ffffff")
    combo_porta.pack(fill="x", padx=10, pady=(0, 10))

    def atualizar_combos():
        drivers = obter_drivers_instalados()
        portas = obter_portas_instaladas()

        combo_driver.configure(values=drivers)
        if drivers:
            combo_driver.set(drivers[0])

        combo_porta.configure(values=portas)
        if portas:
            combo_porta.set(portas[0])

    def acao_criar_impressora():
        nome = entry_nome_disp.get().strip()
        driver = combo_driver.get()
        porta = combo_porta.get()

        if not nome or not driver or not porta:
            messagebox.showwarning("Aviso", "Preencha o nome da impressora e selecione driver e porta!", parent=win)
            return

        try:
            cmd = f"Add-Printer -Name '{nome}' -DriverName '{driver}' -PortName '{porta}' -ErrorAction Stop"
            res = executar_ps(cmd)

            if res.returncode == 0:
                messagebox.showinfo("Sucesso", f"Impressora '{nome}' criada com sucesso vinculada à porta '{porta}' e driver '{driver}'!", parent=win)
                win.destroy()
            else:
                messagebox.showerror("Erro de Instalação", f"Falha ao vincular impressora:\n{res.stderr or res.stdout}", parent=win)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro na operação:\n{str(e)}", parent=win)

    btn_criar_disp = ctk.CTkButton(frame_disp, text="🖨️ Criar e Vincular Impressora", fg_color="#23a55a", hover_color="#1d8a4b", height=35, command=acao_criar_impressora)
    btn_criar_disp.pack(fill="x", padx=10, pady=(5, 12))

    atualizar_combos()

def escanear_impressoras_sistema():
    itens = set()
    chaves = [
        r"SYSTEM\CurrentControlSet\Control\Print\Printers",
        r"SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Drivers\Version-3",
        r"SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Drivers\Version-4"
    ]
    for subkey in chaves:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey, 0, winreg.KEY_READ)
            count = winreg.QueryInfoKey(key)[0]
            for i in range(count):
                itens.add(winreg.EnumKey(key, i))
            winreg.CloseKey(key)
        except Exception:
            pass
    return sorted(list(itens))

def executar_limpeza_item(target):
    executar_ps(f"Remove-Printer -Name '{target}' -ErrorAction SilentlyContinue")
    executar_ps(f"Remove-PrinterDriver -Name '{target}' -ErrorAction SilentlyContinue")

def abrir_janela_limpeza():
    itens = escanear_impressoras_sistema()
    if not itens:
        messagebox.showinfo("Limpeza de Impressoras", "Nenhuma impressora ou driver foi encontrado no sistema.")
        return

    win = ctk.CTkToplevel(root)
    win.title("Limpeza Total de Impressoras e Drivers")
    win.geometry("450x450")
    win.resizable(False, False)
    win.configure(fg_color="#18191c")

    lbl = ctk.CTkLabel(win, text="Selecione o item para remover completamente:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff")
    lbl.pack(pady=10)

    scroll = ctk.CTkScrollableFrame(win, corner_radius=10, fg_color="#202225")
    scroll.pack(fill="both", expand=True, padx=15, pady=(0, 10))

    var_selecionado = ctk.StringVar(value="")

    for item in itens:
        rb = ctk.CTkRadioButton(scroll, text=item, variable=var_selecionado, value=item, text_color="#dcddde")
        rb.pack(anchor="w", pady=5, padx=5)

    def confirmar_remover_um():
        alvo = var_selecionado.get()
        if not alvo:
            messagebox.showwarning("Aviso", "Selecione uma impressora ou driver para remover!")
            return
        if messagebox.askyesno("Confirmar Remocao", f"Tem certeza que deseja remover completamente o item:\n\n{alvo}?"):
            executar_limpeza_item(alvo)
            messagebox.showinfo("Sucesso", f"Item '{alvo}' e todos os seus rastros foram removidos!")
            win.destroy()

    def confirmar_remover_todos():
        if messagebox.askyesno("ATENCAO", "Tem certeza que deseja apagar TODOS os drivers, impressoras e programas de impressão do sistema?"):
            for item in itens:
                executar_limpeza_item(item)
            messagebox.showinfo("Sucesso", "Todos os itens de impressão foram removidos com sucesso!")
            win.destroy()

    btn_um = ctk.CTkButton(win, text="Remover Selecionado", fg_color="#2b2d31", hover_color="#3b3d44", command=confirmar_remover_um)
    btn_um.pack(fill="x", padx=15, pady=(0, 5))

    btn_todos = ctk.CTkButton(win, text="[ EXCLUIR TODOS OS ITENS ]", fg_color="#f23f43", hover_color="#d03135", command=confirmar_remover_todos)
    btn_todos.pack(fill="x", padx=15, pady=(0, 15))

def obter_impressoras_sistema_detalhadas():
    cmd = "Get-Printer | Select-Object Name, PortName, DriverName, Default, PrinterStatus | ConvertTo-Json"
    res = executar_ps(cmd)
    if res.returncode == 0 and res.stdout.strip():
        try:
            dados = json.loads(res.stdout)
            if isinstance(dados, dict):
                return [dados]
            return dados
        except Exception:
            return []
    return []

def abrir_janela_varredura_impressoras():
    win = ctk.CTkToplevel(root)
    win.title("Varredura de Impressoras e Não Especificados")
    win.geometry("520x520")
    win.resizable(False, False)
    win.configure(fg_color="#18191c")

    lbl_titulo = ctk.CTkLabel(win, text="VARREDURA DE IMPRESSORAS E DISPOSITIVOS", font=ctk.CTkFont(size=13, weight="bold"), text_color="#ffffff")
    lbl_titulo.pack(pady=(15, 2))

    lbl_status = ctk.CTkLabel(win, text="Clique abaixo para iniciar a varredura...", font=ctk.CTkFont(size=11), text_color="#949ba4")
    lbl_status.pack(pady=(0, 10))

    scroll_resultados = ctk.CTkScrollableFrame(win, corner_radius=10, fg_color="#202225")
    scroll_resultados.pack(fill="both", expand=True, padx=15, pady=(0, 10))

    def eh_impressora_ip(ip, timeout=0.5):
        portas = [9100, 515, 631]
        for porta in portas:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                res = s.connect_ex((ip, porta))
                s.close()
                if res == 0:
                    return True
            except Exception:
                pass
        return False

    def executar_varredura():
        btn_iniciar.configure(state="disabled", text="⏳ Varrendo Sistema e Rede...")
        lbl_status.configure(text="Buscando impressoras USB / Não Especificadas e varrendo a rede...", text_color="#f0b232")
        
        for widget in scroll_resultados.winfo_children():
            widget.destroy()

        impressoras_win = obter_impressoras_sistema_detalhadas()
        
        if impressoras_win:
            lbl_cat_win = ctk.CTkLabel(scroll_resultados, text="📌 IMPRESSORAS / DISPOSITIVOS INSTALADOS NO WINDOWS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#4752c4", anchor="w")
            lbl_cat_win.pack(fill="x", padx=5, pady=(5, 5))

            for imp in impressoras_win:
                nome = imp.get("Name", "Desconhecida")
                porta = imp.get("PortName", "N/A")
                is_default = imp.get("Default", False)
                
                frame_item = ctk.CTkFrame(scroll_resultados, fg_color="#2b2d31", corner_radius=6)
                frame_item.pack(fill="x", pady=3, padx=5)

                txt_default = " ★ (Padrão)" if is_default else ""
                lbl_nome = ctk.CTkLabel(frame_item, text=f"🖨️ {nome}{txt_default}\n📍 Porta: {porta}", font=ctk.CTkFont(size=11), text_color="#ffffff", justify="left", anchor="w")
                lbl_nome.pack(side="left", padx=10, pady=6)

                if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', porta):
                    def selecionar_ip_win(ip_sel=porta):
                        entry_novo_ip.delete(0, "end")
                        entry_novo_ip.insert(0, ip_sel)
                        ao_digitar_novo_ip()
                        win.destroy()

                    btn_usar_ip = ctk.CTkButton(frame_item, text="Usar IP", font=ctk.CTkFont(size=11), fg_color="#23a55a", hover_color="#1d8a4b", width=70, height=26, command=selecionar_ip_win)
                    btn_usar_ip.pack(side="right", padx=10, pady=5)

        lbl_cat_rede = ctk.CTkLabel(scroll_resultados, text="🌐 IMPRESSORAS ENCONTRADAS NA REDE LOCAL (RAW / PORTA 9100)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#23a55a", anchor="w")
        lbl_cat_rede.pack(fill="x", padx=5, pady=(15, 5))

        ip_atual = entry_ip_atual.get().strip()
        partes = ip_atual.split(".")
        if len(partes) == 4:
            prefixo = f"{partes[0]}.{partes[1]}.{partes[2]}."
        else:
            prefixo = "192.168.1."

        encontrados = []

        def checar(ip):
            if eh_impressora_ip(ip):
                encontrados.append(ip)

        threads = []
        for i in range(1, 255):
            target = f"{prefixo}{i}"
            t = threading.Thread(target=checar, args=(target,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        if encontrados:
            for ip in encontrados:
                frame_item = ctk.CTkFrame(scroll_resultados, fg_color="#2b2d31", corner_radius=6)
                frame_item.pack(fill="x", pady=3, padx=5)

                lbl_ip_item = ctk.CTkLabel(frame_item, text=f"🌐 IP Detectado: {ip}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff")
                lbl_ip_item.pack(side="left", padx=10, pady=8)

                def selecionar_ip(ip_sel=ip):
                    entry_novo_ip.delete(0, "end")
                    entry_novo_ip.insert(0, ip_sel)
                    ao_digitar_novo_ip()
                    win.destroy()

                btn_usar = ctk.CTkButton(frame_item, text="Usar este IP", font=ctk.CTkFont(size=11), fg_color="#4752c4", hover_color="#3c45a5", width=90, height=28, command=selecionar_ip)
                btn_usar.pack(side="right", padx=10, pady=5)
        else:
            lbl_vazio = ctk.CTkLabel(scroll_resultados, text="Nenhuma impressora de rede respondeu na faixa de IP.", text_color="#949ba4")
            lbl_vazio.pack(pady=10)

        lbl_status.configure(text=f"Varredura concluída! {len(encontrados)} impressora(s) de rede encontrada(s).", text_color="#23a55a")
        btn_iniciar.configure(state="normal", text="🔄 Atualizar Varredura")

    def iniciar_thread():
        threading.Thread(target=executar_varredura, daemon=True).start()

    btn_iniciar = ctk.CTkButton(win, text="🔍 Iniciar Varredura de Dispositivos e Rede", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#4752c4", hover_color="#3c45a5", height=38, command=iniciar_thread)
    btn_iniciar.pack(fill="x", padx=15, pady=(0, 15))

cache_dados = carregar_cache()

root = ctk.CTk()
root.title("Configurador de Rede e Impressoras")
root.geometry("520x880")
root.resizable(False, False)
root.configure(fg_color="#18191c")

# --- BARRA SUPERIOR MINÚSCULA PARA BOTÃO DISCRETO ---
frame_top_bar = ctk.CTkFrame(root, fg_color="transparent", height=24)
frame_top_bar.pack(fill="x", padx=12, pady=(6, 0))

# Botão minúsculo [ ] no canto superior direito para organizar janelas
btn_grid_top = ctk.CTkButton(
    frame_top_bar,
    text="[ ]",
    width=28,
    height=22,
    font=ctk.CTkFont(size=11, weight="bold"),
    fg_color="#2b2d31",
    hover_color="#3b3d44",
    text_color="#949ba4",
    corner_radius=4,
    command=organizar_janelas_grade
)
btn_grid_top.pack(side="right")

icon_file = resource_path("icon.ico")
if os.path.exists(icon_file):
    root.iconbitmap(icon_file)

frame = ctk.CTkScrollableFrame(root, corner_radius=15, fg_color="#1e1f22")
frame.pack(fill="both", expand=True, padx=12, pady=(4, 12))

# --- CABEÇALHO COM LOGOTIPO ---
if os.path.exists(icon_file):
    try:
        pil_image = Image.open(icon_file)
        logo_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(80, 80))
        lbl_logo = ctk.CTkLabel(frame, image=logo_image, text="")
        lbl_logo.pack(pady=(10, 0))
    except Exception as e:
        print(f"Erro ao carregar logo na interface: {e}")

lbl_titulo = ctk.CTkLabel(frame, text="PAINEL DE CONFIGURAÇÃO DE REDE", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff")
lbl_titulo.pack(pady=(10, 12))

# --- SEÇÃO: ENTRADA PRINCIPAL ---
frame_principal = ctk.CTkFrame(frame, corner_radius=10, fg_color="#2b2d31")
frame_principal.pack(fill="x", pady=(0, 10), padx=5)

lbl_4 = ctk.CTkLabel(frame_principal, text="Endereço IP da Impressora:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff", anchor="w")
lbl_4.pack(fill="x", padx=12, pady=(10, 4))

entry_novo_ip = ctk.CTkEntry(frame_principal, corner_radius=8, fg_color="#1e1f22", border_color="#383a40", text_color="#ffffff", placeholder_text="Ex: 192.168.10.50")
entry_novo_ip.insert(0, cache_dados.get("novo_ip", "192.168.10.50"))
entry_novo_ip.bind("<KeyRelease>", ao_digitar_novo_ip)
entry_novo_ip.pack(fill="x", padx=12, pady=(0, 8))

# --- SELEÇÃO MANUAL DO ADAPTADOR ---
lbl_adaptador_sel = ctk.CTkLabel(frame_principal, text="Adaptador de Rede:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff", anchor="w")
lbl_adaptador_sel.pack(fill="x", padx=12, pady=(4, 4))

seg_adaptador = ctk.CTkSegmentedButton(
    frame_principal,
    values=["Cabo", "Wi-Fi"],
    selected_color="#4752c4",
    selected_hover_color="#3c45a5",
    unselected_color="#1e1f22",
    unselected_hover_color="#383a40",
    text_color="#ffffff"
)
seg_adaptador.set(cache_dados.get("adaptador", "Cabo"))
seg_adaptador.pack(fill="x", padx=12, pady=(0, 12))

# --- SPOILER: CONFIGURAÇÕES AVANÇADAS ---
spoiler_aberto = False
btn_spoiler = ctk.CTkButton(
    frame, 
    text="▶ 🛠️ Exibir Configurações Avançadas de Rede", 
    fg_color="transparent", 
    text_color="#949ba4",
    hover_color="#2b2d31",
    anchor="w",
    command=alternar_spoiler
)
btn_spoiler.pack(fill="x", pady=(0, 8))

frame_spoiler = ctk.CTkFrame(frame, corner_radius=10, fg_color="#2b2d31")

lbl_2 = ctk.CTkLabel(frame_spoiler, text="1. Seu IP Principal ATUAL:", text_color="#dcddde", anchor="w")
lbl_2.pack(fill="x", padx=10, pady=(10, 2))
entry_ip_atual = ctk.CTkEntry(frame_spoiler, corner_radius=8, fg_color="#1e1f22", border_color="#383a40", text_color="#ffffff")
entry_ip_atual.pack(fill="x", padx=10, pady=(0, 10))

lbl_3 = ctk.CTkLabel(frame_spoiler, text="2. Seu Gateway ATUAL:", text_color="#dcddde", anchor="w")
lbl_3.pack(fill="x", padx=10, pady=(0, 2))
entry_gw_atual = ctk.CTkEntry(frame_spoiler, corner_radius=8, fg_color="#1e1f22", border_color="#383a40", text_color="#ffffff")
entry_gw_atual.pack(fill="x", padx=10, pady=(0, 10))

lbl_5 = ctk.CTkLabel(frame_spoiler, text="3. Máscara de sub-rede nova:", text_color="#dcddde", anchor="w")
lbl_5.pack(fill="x", padx=10, pady=(0, 2))
entry_mascara = ctk.CTkEntry(frame_spoiler, corner_radius=8, fg_color="#1e1f22", border_color="#383a40", text_color="#ffffff")
entry_mascara.insert(0, cache_dados.get("mascara", "255.255.255.0"))
entry_mascara.pack(fill="x", padx=10, pady=(0, 10))

lbl_6 = ctk.CTkLabel(frame_spoiler, text="4. NOVO Gateway secundário (Auto-preenchido):", text_color="#dcddde", anchor="w")
lbl_6.pack(fill="x", padx=10, pady=(0, 2))
entry_novo_gw = ctk.CTkEntry(frame_spoiler, corner_radius=8, fg_color="#1e1f22", border_color="#383a40", text_color="#ffffff")
entry_novo_gw.insert(0, cache_dados.get("novo_gw", "192.168.10.1"))
entry_novo_gw.pack(fill="x", padx=10, pady=(0, 10))

def auto_preencher_rede_tempo_real():
    auto_adaptador, auto_ip, auto_gw = detectar_rede_automatica_cmd()
    
    seg_adaptador.set(auto_adaptador or cache_dados.get("adaptador", "Cabo"))
    
    entry_ip_atual.delete(0, "end")
    entry_ip_atual.insert(0, auto_ip or cache_dados.get("ip_atual", "192.168."))
    
    entry_gw_atual.delete(0, "end")
    entry_gw_atual.insert(0, auto_gw or cache_dados.get("gw_atual", "192.168."))

auto_preencher_rede_tempo_real()

# --- BLOCO: AÇÕES DE REDE ---
frame_acoes_rede = ctk.CTkFrame(frame, corner_radius=10, fg_color="transparent")
frame_acoes_rede.pack(fill="x", pady=(0, 10))

btn_aplicar = ctk.CTkButton(
    frame_acoes_rede, 
    text="⚡ Aplicar Configuração de Rede", 
    font=ctk.CTkFont(size=12, weight="bold"),
    fg_color="#23a55a", 
    hover_color="#1d8a4b", 
    corner_radius=8,
    height=40,
    command=aplicar_config
)
btn_aplicar.pack(fill="x")

# --- BLOCO: GERENCIAMENTO DE IMPRESSORAS ---
lbl_sub_imp = ctk.CTkLabel(frame, text="GERENCIAMENTO E DISPOSITIVOS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#949ba4", anchor="w")
lbl_sub_imp.pack(fill="x", padx=5, pady=(5, 5))

btn_central_drivers = ctk.CTkButton(
    frame, 
    text="📦 Central de Drivers (Links Direct)", 
    font=ctk.CTkFont(size=12, weight="bold"),
    fg_color="#4752c4", 
    hover_color="#3c45a5", 
    corner_radius=8,
    height=36,
    command=abrir_janela_drivers
)
btn_central_drivers.pack(fill="x", pady=(0, 8))

frame_grid_imp = ctk.CTkFrame(frame, fg_color="transparent")
frame_grid_imp.pack(fill="x", pady=(0, 10))

btn_criar_disp_janela = ctk.CTkButton(
    frame_grid_imp, 
    text="➕ Criar Dispositivo/Porta", 
    font=ctk.CTkFont(size=11, weight="bold"),
    fg_color="#2b2d31", 
    hover_color="#3b3d44", 
    border_width=1,
    border_color="#383a40",
    corner_radius=8,
    height=36,
    command=abrir_janela_criar_dispositivo
)
btn_criar_disp_janela.pack(side="left", fill="x", expand=True, padx=(0, 4))

btn_ajuste_imp = ctk.CTkButton(
    frame_grid_imp, 
    text="🌐 Configurar IP Impressora", 
    font=ctk.CTkFont(size=11, weight="bold"),
    fg_color="#2b2d31", 
    hover_color="#3b3d44", 
    border_width=1,
    border_color="#383a40",
    corner_radius=8,
    height=36,
    command=abrir_janela_ajuste_impressora
)
btn_ajuste_imp.pack(side="right", fill="x", expand=True, padx=(4, 0))

# --- BLOCO: FERRAMENTAS DO SISTEMA ---
frame_duplo = ctk.CTkFrame(frame, fg_color="transparent")
frame_duplo.pack(fill="x", pady=(0, 8))

btn_spooler = ctk.CTkButton(
    frame_duplo, 
    text="🔄 Reiniciar Spooler", 
    font=ctk.CTkFont(size=11, weight="bold"),
    fg_color="#2b2d31", 
    hover_color="#3b3d44", 
    border_width=1,
    border_color="#383a40",
    corner_radius=8,
    height=36,
    command=reiniciar_spooler
)
btn_spooler.pack(side="left", fill="x", expand=True, padx=(0, 4))

btn_control = ctk.CTkButton(
    frame_duplo, 
    text="🖨️ Abrir Impressoras", 
    font=ctk.CTkFont(size=11, weight="bold"),
    fg_color="#2b2d31", 
    hover_color="#3b3d44", 
    border_width=1,
    border_color="#383a40",
    corner_radius=8,
    height=36,
    command=abrir_control_printers
)
btn_control.pack(side="right", fill="x", expand=True, padx=(4, 0))

# --- BLOCO: MANUTENÇÃO E RESTAURAÇÃO ---
lbl_sub_manut = ctk.CTkLabel(frame, text="MANUTENÇÃO E RESTAURAÇÃO", font=ctk.CTkFont(size=11, weight="bold"), text_color="#949ba4", anchor="w")
lbl_sub_manut.pack(fill="x", padx=5, pady=(5, 5))

btn_limpeza = ctk.CTkButton(
    frame, 
    text="🧹 Limpeza Total de Impressoras e Drivers", 
    font=ctk.CTkFont(size=11, weight="bold"),
    fg_color="#2b2d31", 
    hover_color="#3b3d44", 
    border_width=1,
    border_color="#383a40",
    corner_radius=8,
    height=36,
    command=abrir_janela_limpeza
)
btn_limpeza.pack(fill="x", pady=(0, 8))

btn_varredura_rede = ctk.CTkButton(
    frame, 
    text="🔍 Varrer Dispositivos e Rede (IP / Não Especificados)", 
    font=ctk.CTkFont(size=11, weight="bold"),
    fg_color="#2b2d31", 
    hover_color="#3b3d44", 
    border_width=1,
    border_color="#383a40",
    corner_radius=8,
    height=36,
    command=abrir_janela_varredura_impressoras
)
btn_varredura_rede.pack(fill="x", pady=(0, 8))

btn_restaurar = ctk.CTkButton(
    frame, 
    text="Restaurar DHCP Padrão", 
    font=ctk.CTkFont(size=12, weight="bold"),
    fg_color="#f23f43", 
    hover_color="#d03135", 
    corner_radius=8,
    height=38,
    command=restaurar_dhcp
)
btn_restaurar.pack(fill="x", pady=(0, 12))

# --- INSTRUÇÕES E RODAPÉ ---
frame_instrucoes = ctk.CTkFrame(frame, corner_radius=10, fg_color="#2b2d31")
frame_instrucoes.pack(fill="x", pady=(0, 5))

lbl_inst_titulo = ctk.CTkLabel(
    frame_instrucoes, 
    text="📌 DICAS DE USO", 
    font=ctk.CTkFont(size=11, weight="bold"),
    text_color="#ffffff"
)
lbl_inst_titulo.pack(anchor="w", padx=12, pady=(8, 4))

texto_instrucoes = (
    "1. Insira o IP da impressora e selecione Cabo ou Wi-Fi.\n"
    "2. Clique em 'Aplicar Configuração de Rede'.\n"
    "3. Use o ícone [ ] no topo direito para alinhar janelas na tela."
)

lbl_inst_corpo = ctk.CTkLabel(
    frame_instrucoes, 
    text=texto_instrucoes, 
    font=ctk.CTkFont(size=11),
    text_color="#949ba4",
    justify="left",
    anchor="w"
)
lbl_inst_corpo.pack(fill="x", padx=12, pady=(0, 10))

root.mainloop()
