import ctypes
import sys
import subprocess
import json
import os
import customtkinter as ctk
from tkinter import messagebox

CACHE_FILE = "config_cache.json"

# Configuração do Tema Visual Moderno
ctk.set_appearance_mode("System")  # Segue o tema do Windows (Dark / Light)
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

def detectar_rede_automatica():
    """Coleta automaticamente o tipo de adaptador (1 ou 2), IP atual e Gateway atual"""
    try:
        # Comando PowerShell para obter a interface de rede IPv4 ativa com Gateway padrão
        ps_cmd = (
            "Get-NetRoute -DestinationPrefix '0.0.0.0/0' | "
            "Get-NetIPInterface -AddressFamily IPv4 | "
            "Select-Object -First 1 InterfaceAlias, InterfaceIndex"
        )
        res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
        
        if res.returncode == 0 and res.stdout.strip():
            # Pega o nome do adaptador ativo
            ps_adapter = (
                "Get-NetRoute -DestinationPrefix '0.0.0.0/0' | "
                "Select-Object -First 1 -ExpandProperty InterfaceAlias"
            )
            adapter_name = subprocess.run(["powershell", "-Command", ps_adapter], capture_output=True, text=True).stdout.strip()

            # Pega o IP Atual
            ps_ip = f"(Get-NetIPAddress -InterfaceAlias '{adapter_name}' -AddressFamily IPv4).IPAddress"
            ip_atual = subprocess.run(["powershell", "-Command", ps_ip], capture_output=True, text=True).stdout.strip().split('\n')[0].strip()

            # Pega o Gateway Atual
            ps_gw = f"(Get-NetRoute -InterfaceAlias '{adapter_name}' -DestinationPrefix '0.0.0.0/0').NextHop"
            gw_atual = subprocess.run(["powershell", "-Command", ps_gw], capture_output=True, text=True).stdout.strip().split('\n')[0].strip()

            # Mapeia para 1 (Wi-Fi) ou 2 (Ethernet/Cabo)
            codigo_adaptador = "1" if "wi-fi" in adapter_name.lower() or "wireless" in adapter_name.lower() else "2"

            return codigo_adaptador, ip_atual, gw_atual
    except Exception as e:
        print(f"Erro ao auto-detectar rede: {e}")
    
    return "", "", ""

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

# Tenta ler o cache
cache_dados = carregar_cache()

# Tenta auto-detectar rede atual
auto_adaptador, auto_ip, auto_gw = detectar_rede_automatica()

# --- CONSTRUÇÃO DA INTERFACE MODERNA (CustomTkinter) ---
root = ctk.CTk()
root.title("Configurador de Rede - Fluxo Contínuo")
root.geometry("500x700")
root.resizable(False, False)

# Container Principal com Scroll suave
frame = ctk.CTkScrollableFrame(root, corner_radius=15)
frame.pack(fill="both", expand=True, padx=15, pady=15)

# Título Principal
lbl_titulo = ctk.CTkLabel(frame, text="PASSO 1: CONFIGURAÇÃO DE IP + IMPRESSORA", font=ctk.CTkFont(size=14, weight="bold"))
lbl_titulo.pack(pady=(10, 15))

# Campo 1
lbl_1 = ctk.CTkLabel(frame, text="1. Wi-Fi digite 1, Cabo de rede digite 2:", anchor="w")
lbl_1.pack(fill="x", pady=(0, 2))
entry_adaptador = ctk.CTkEntry(frame, corner_radius=10, placeholder_text="1 para Wi-Fi ou 2 para Cabo")
entry_adaptador.insert(0, auto_adaptador or cache_dados.get("adaptador", ""))
entry_adaptador.pack(fill="x", pady=(0, 10))

# Campo 2
lbl_2 = ctk.CTkLabel(frame, text="2. Seu IP Principal ATUAL (Auto-detectado):", anchor="w")
lbl_2.pack(fill="x", pady=(0, 2))
entry_ip_atual = ctk.CTkEntry(frame, corner_radius=10)
entry_ip_atual.insert(0, auto_ip or cache_dados.get("ip_atual", "192.168."))
entry_ip_atual.pack(fill="x", pady=(0, 10))

# Campo 3
lbl_3 = ctk.CTkLabel(frame, text="3. Seu Gateway ATUAL (Auto-detectado):", anchor="w")
lbl_3.pack(fill="x", pady=(0, 2))
entry_gw_atual = ctk.CTkEntry(frame, corner_radius=10)
entry_gw_atual.insert(0, auto_gw or cache_dados.get("gw_atual", "192.168."))
entry_gw_atual.pack(fill="x", pady=(0, 20))

# Separador / Subtítulo
lbl_sub = ctk.CTkLabel(frame, text="DADOS DA NOVA REDE (Impressora)", font=ctk.CTkFont(size=13, weight="bold"))
lbl_sub.pack(anchor="w", pady=(0, 8))

# Caixa Informativa Arredondada
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

# Campo 4
lbl_4 = ctk.CTkLabel(frame, text="4. NOVO IP secundário (ex: 192.168.10.51):", anchor="w")
lbl_4.pack(fill="x", pady=(0, 2))
entry_novo_ip = ctk.CTkEntry(frame, corner_radius=10)
entry_novo_ip.insert(0, cache_dados.get("novo_ip", "192.168."))
entry_novo_ip.pack(fill="x", pady=(0, 10))

# Campo 5
lbl_5 = ctk.CTkLabel(frame, text="5. Máscara de sub-rede nova (ex: 255.255.255.0):", anchor="w")
lbl_5.pack(fill="x", pady=(0, 2))
entry_mascara = ctk.CTkEntry(frame, corner_radius=10)
entry_mascara.insert(0, cache_dados.get("mascara", "255.255.255.0"))
entry_mascara.pack(fill="x", pady=(0, 10))

# Campo 6
lbl_6 = ctk.CTkLabel(frame, text="6. NOVO Gateway secundário (ex: 192.168.10.1):", anchor="w")
lbl_6.pack(fill="x", pady=(0, 2))
entry_novo_gw = ctk.CTkEntry(frame, corner_radius=10)
entry_novo_gw.insert(0, cache_dados.get("novo_gw", "192.168."))
entry_novo_gw.pack(fill="x", pady=(0, 20))

# Botões Arredondados
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
