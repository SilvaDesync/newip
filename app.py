import ctypes
import sys
import subprocess
import json
import os
import re
import customtkinter as ctk
from tkinter import messagebox

CACHE_FILE = "config_cache.json"

# Configuração do Tema Visual Moderno
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def check_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not check_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

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
    valor = valor.strip()
    if valor == "1":
        return "Wi-Fi"
    elif valor == "2":
        return "Ethernet"
    return valor

def detectar_rede_automatica_cmd():
    adaptador_codigo = ""
    ip_atual = ""
    gw_atual = ""

    try:
        res = subprocess.run("ipconfig", shell=True, capture_output=True, text=True, encoding="cp850", errors="ignore")
        output = res.stdout

        bloco_atual = None
        for linha in output.splitlines():
            linha_strip = linha.strip()

            if "Adaptador" in linha or "adapter" in linha:
                bloco_atual = linha_strip

            elif "IPv4" in linha_strip and bloco_atual:
                match_ip = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', linha_strip)
                if match_ip:
                    ip_temp = match_ip.group(1)
                    if not ip_temp.startswith("127.") and not ip_temp.startswith("169.254."):
                        ip_atual = ip_temp
                        if "wi-fi" in bloco_atual.lower() or "sem fio" in bloco_atual.lower() or "wireless" in bloco_atual.lower():
                            adaptador_codigo = "1"
                        else:
                            adaptador_codigo = "2"

            elif ("Gateway Padr" in linha_strip or "Default Gateway" in linha_strip) and ip_atual:
                match_gw = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', linha_strip)
                if match_gw:
                    gw_atual = match_gw.group(1)
                    break

    except Exception as e:
        print(f"Erro ao auto-detectar via CMD: {e}")

    return adaptador_codigo, ip_atual, gw_atual

def ao_digitar_novo_ip(event=None):
    """Calcula e preenche o gateway secundário terminado em .1 automaticamente"""
    ip_texto = entry_novo_ip.get().strip()
    partes = ip_texto.split(".")
    if len(partes) == 4 and all(p.isdigit() for p in partes[:3]):
        gateway_auto = f"{partes[0]}.{partes[1]}.{partes[2]}.1"
        entry_novo_gw.delete(0, "end")
        entry_novo_gw.insert(0, gateway_auto)

def alternar_spoiler():
    """Abre e fecha a seção dos campos 1, 2 e 3"""
    global spoiler_aberto
    if spoiler_aberto:
        frame_spoiler.pack_forget()
        btn_spoiler.configure(text="▶ 🛠️ Editar Dados do Computador (Rede Atual)")
        spoiler_aberto = False
    else:
        frame_spoiler.pack(fill="x", pady=(0, 15), before=lbl_sub)
        btn_spoiler.configure(text="▼ 🛠️ Ocultar Dados do Computador")
        spoiler_aberto = True

def aplicar_config():
    adaptador_raw = entry_adaptador.get()
    adaptador = obter_nome_adaptador(adaptador_raw)
    
    ip_atual = entry_ip_atual.get().strip()
    gw_atual = entry_gw_atual.get().strip()
    novo_ip = entry_novo_ip.get().strip()
    mascara = entry_mascara.get().strip()
    novo_gw = entry_novo_gw.get().strip()

    if not all([adaptador, ip_atual, gw_atual, novo_ip, mascara, novo_gw]):
        messagebox.showwarning("Aviso", "Por favor, preencha todos os campos!")
        return

    dados_para_salvar = {
        "adaptador": adaptador_raw,
        "ip_atual": ip_atual,
        "gw_atual": gw_atual,
        "novo_ip": novo_ip,
        "mascara": mascara,
        "novo_gw": novo_gw
    }
    salvar_cache(dados_para_salvar)

    try:
        cmd1 = f'netsh interface ipv4 set address name="{adaptador}" static {ip_atual} {mascara} {gw_atual} 1'
        res1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True)
        if res1.returncode != 0:
            raise Exception(f"Passo 1 (Fixar IP):\n{res1.stderr or res1.stdout}")

        cmd2 = f'netsh interface ipv4 add address name="{adaptador}" {novo_ip} {mascara}'
        res2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
        if res2.returncode != 0:
            raise Exception(f"Passo 2 (Adicionar IP):\n{res2.stderr or res2.stdout}")

        cmd3 = f'netsh interface ipv4 add address name="{adaptador}" gateway={novo_gw} gwmetric=2'
        res3 = subprocess.run(cmd3, shell=True, capture_output=True, text=True)
        if res3.returncode != 0:
            raise Exception(f"Passo 3 (Adicionar Gateway):\n{res3.stderr or res3.stdout}")

        messagebox.showinfo("Sucesso", f"REDE CONFIGURADA COM SUCESSO!\nAdaptador: {adaptador}\nA rede do cliente e a impressora já estão ativas.")

    except Exception as e:
        messagebox.showerror("Erro de Configuração", f"Falha ao aplicar configurações:\n\n{str(e)}")

def restaurar_dhcp():
    adaptador_raw = entry_adaptador.get()
    adaptador = obter_nome_adaptador(adaptador_raw)
    
    if not adaptador:
        messagebox.showwarning("Aviso", "O campo 'Nome do Adaptador' precisa estar preenchido para restaurar!")
        return

    try:
        cmd1 = f'netsh interface ipv4 set address name="{adaptador}" source=dhcp'
        subprocess.run(cmd1, shell=True, capture_output=True, text=True)

        cmd2 = f'netsh interface ipv4 set dns name="{adaptador}" source=dhcp'
        subprocess.run(cmd2, shell=True, capture_output=True, text=True)

        messagebox.showinfo("Sucesso", f"Rede do adaptador '{adaptador}' restaurada com sucesso para DHCP automático!")
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao restaurar DHCP:\n{str(e)}")

# Carrega cache e auto-detecta rede
cache_dados = carregar_cache()
auto_adaptador, auto_ip, auto_gw = detectar_rede_automatica_cmd()

# --- INTERFACE MODERNA ---
root = ctk.CTk()
root.title("Configurador de Rede - Fluxo Contínuo")
root.geometry("500x680")
root.resizable(False, False)

frame = ctk.CTkScrollableFrame(root, corner_radius=15)
frame.pack(fill="both", expand=True, padx=15, pady=15)

lbl_titulo = ctk.CTkLabel(frame, text="PASSO 1: CONFIGURAÇÃO DE IP + IMPRESSORA", font=ctk.CTkFont(size=14, weight="bold"))
lbl_titulo.pack(pady=(10, 15))

# Botão Spoiler/Expansível
spoiler_aberto = False
btn_spoiler = ctk.CTkButton(
    frame, 
    text="▶ 🛠️ Editar Dados do Computador (Rede Atual)", 
    fg_color="transparent", 
    text_color=("gray10", "gray90"),
    hover_color=("gray85", "gray25"),
    anchor="w",
    command=alternar_spoiler
)
btn_spoiler.pack(fill="x", pady=(0, 10))

# Container interno do Spoiler (oculto por padrão)
frame_spoiler = ctk.CTkFrame(frame, corner_radius=10, fg_color=("gray90", "gray20"))

lbl_1 = ctk.CTkLabel(frame_spoiler, text="1. Wi-Fi digite 1, Cabo de rede digite 2:", anchor="w")
lbl_1.pack(fill="x", padx=10, pady=(10, 2))
entry_adaptador = ctk.CTkEntry(frame_spoiler, corner_radius=8)
entry_adaptador.insert(0, auto_adaptador or cache_dados.get("adaptador", ""))
entry_adaptador.pack(fill="x", padx=10, pady=(0, 10))

lbl_2 = ctk.CTkLabel(frame_spoiler, text="2. Seu IP Principal ATUAL:", anchor="w")
lbl_2.pack(fill="x", padx=10, pady=(0, 2))
entry_ip_atual = ctk.CTkEntry(frame_spoiler, corner_radius=8)
entry_ip_atual.insert(0, auto_ip or cache_dados.get("ip_atual", "192.168."))
entry_ip_atual.pack(fill="x", padx=10, pady=(0, 10))

lbl_3 = ctk.CTkLabel(frame_spoiler, text="3. Seu Gateway ATUAL:", anchor="w")
lbl_3.pack(fill="x", padx=10, pady=(0, 2))
entry_gw_atual = ctk.CTkEntry(frame_spoiler, corner_radius=8)
entry_gw_atual.insert(0, auto_gw or cache_dados.get("gw_atual", "192.168."))
entry_gw_atual.pack(fill="x", padx=10, pady=(0, 10))

# Subtítulo Nova Rede
lbl_sub = ctk.CTkLabel(frame, text="DADOS DA NOVA REDE (Impressora)", font=ctk.CTkFont(size=13, weight="bold"))
lbl_sub.pack(anchor="w", pady=(0, 8))

# Caixa Informativa
texto_explicacao = (
    "💡 IMPORTANTE (Regra de Jogo):\n"
    "Cada aparelho na rede precisa ter um número final DIFERENTE!\n"
    "Se o IP da impressora for 192.168.10.50, use ex: 192.168.10.51."
)
lbl_aviso = ctk.CTkLabel(
    frame, 
    text=texto_explicacao, 
    font=ctk.CTkFont(size=11),
    fg_color=("#FFF3CD", "#3D3200"),
    text_color=("#856404", "#FFECB3"),
    corner_radius=10,
    justify="left",
    anchor="w",
    padx=12,
    pady=10
)
lbl_aviso.pack(fill="x", pady=(0, 15))

# Campo 4 (com evento de auto-completar Gateway)
lbl_4 = ctk.CTkLabel(frame, text="4. NOVO IP secundário (ex: 192.168.10.51):", anchor="w")
lbl_4.pack(fill="x", pady=(0, 2))
entry_novo_ip = ctk.CTkEntry(frame, corner_radius=10)
entry_novo_ip.insert(0, cache_dados.get("novo_ip", "192.168."))
entry_novo_ip.bind("<KeyRelease>", ao_digitar_novo_ip)
entry_novo_ip.pack(fill="x", pady=(0, 10))

# Campo 5 (Pré-preenchido com 255.255.255.0)
lbl_5 = ctk.CTkLabel(frame, text="5. Máscara de sub-rede nova:", anchor="w")
lbl_5.pack(fill="x", pady=(0, 2))
entry_mascara = ctk.CTkEntry(frame, corner_radius=10)
entry_mascara.insert(0, cache_dados.get("mascara", "255.255.255.0"))
entry_mascara.pack(fill="x", pady=(0, 10))

# Campo 6 (Preenchido automaticamente ao digitar no Campo 4)
lbl_6 = ctk.CTkLabel(frame, text="6. NOVO Gateway secundário (Auto-preenchido):", anchor="w")
lbl_6.pack(fill="x", pady=(0, 2))
entry_novo_gw = ctk.CTkEntry(frame, corner_radius=10)
entry_novo_gw.insert(0, cache_dados.get("novo_gw", "192.168.10.1"))
entry_novo_gw.pack(fill="x", pady=(0, 20))

# Botões
btn_aplicar = ctk.CTkButton(
    frame, 
    text="Aplicar Configuração", 
    font=ctk.CTkFont(size=12, weight="bold"),
    fg_color="#28a745", 
    hover_color="#218838", 
    corner_radius=12,
    height=40,
    command=aplicar_config
)
btn_aplicar.pack(fill="x", pady=(0, 10))

btn_restaurar = ctk.CTkButton(
    frame, 
    text="Restaurar DHCP (Sair)", 
    font=ctk.CTkFont(size=12, weight="bold"),
    fg_color="#dc3545", 
    hover_color="#c82333", 
    corner_radius=12,
    height=40,
    command=restaurar_dhcp
)
btn_restaurar.pack(fill="x", pady=(0, 10))

root.mainloop()
