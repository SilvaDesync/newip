import ctypes
import sys
import subprocess
import json
import os
import tkinter as tk
from tkinter import messagebox

CACHE_FILE = "config_cache.json"

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

    # Salva os dados no arquivo de cache
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
        # Passo 1: Fixar IP principal
        cmd1 = f'netsh interface ipv4 set address name="{adaptador}" static {ip_atual} {mascara} {gw_atual} 1'
        res1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True)
        if res1.returncode != 0:
            raise Exception(f"Passo 1 (Fixar IP):\n{res1.stderr or res1.stdout}")

        # Passo 2: Adicionar IP secundário
        cmd2 = f'netsh interface ipv4 add address name="{adaptador}" {novo_ip} {mascara}'
        res2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
        if res2.returncode != 0:
            raise Exception(f"Passo 2 (Adicionar IP):\n{res2.stderr or res2.stdout}")

        # Passo 3: Adicionar Gateway secundário
        cmd3 = f'netsh interface ipv4 add address name="{adaptador}" gateway={novo_gw} gwmetric=2'
        res3 = subprocess.run(cmd3, shell=True, capture_output=True, text=True)
        if res3.returncode != 0:
            raise Exception(f"Passo 3 (Adicionar Gateway):\n{res3.stderr or res3.stdout}")

        messagebox.showinfo("Sucesso", f"REDE CONFIGURADA COM SUCESSO!\nAdaptador configurado: {adaptador}\nA rede do cliente e a impressora já estão ativas.")

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
        res1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True)

        cmd2 = f'netsh interface ipv4 set dns name="{adaptador}" source=dhcp'
        res2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)

        messagebox.showinfo("Sucesso", f"Rede do adaptador '{adaptador}' restaurada com sucesso para DHCP automático!")
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao restaurar DHCP:\n{str(e)}")

# Carrega cache prévio se existir
cache_dados = carregar_cache()

# Interface Gráfica
root = tk.Tk()
root.title("Configurador de Rede - Fluxo Contínuo")
root.geometry("480x640")
root.resizable(False, False)
root.configure(padx=20, pady=15)

tk.Label(root, text="PASSO 1: CONFIGURAÇÃO DE IP + IMPRESSORA", font=("Arial", 11, "bold")).pack(pady=(0, 10))

# Campo 1
tk.Label(root, text="1. Wi-Fi digite 1, Cabo de rede digite 2:").pack(anchor="w")
entry_adaptador = tk.Entry(root, width=55)
entry_adaptador.insert(0, cache_dados.get("adaptador", ""))
entry_adaptador.pack(pady=(0, 8))

# Campo 2
tk.Label(root, text="2. Seu IP Principal ATUAL:").pack(anchor="w")
entry_ip_atual = tk.Entry(root, width=55)
entry_ip_atual.insert(0, cache_dados.get("ip_atual", "192.168."))
entry_ip_atual.pack(pady=(0, 8))

# Campo 3
tk.Label(root, text="3. Seu Gateway ATUAL:").pack(anchor="w")
entry_gw_atual = tk.Entry(root, width=55)
entry_gw_atual.insert(0, cache_dados.get("gw_atual", "192.168."))
entry_gw_atual.pack(pady=(0, 15))

# Grupo Dados da Nova Rede
tk.Label(root, text="DADOS DA NOVA REDE (Impressora)", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))

# Explicação Didática
texto_explicacao = (
    "💡 IMPORTANTE (Como uma regra de jogo):\n"
    "Cada aparelho na rede precisa ter um número (IP) DIFERENTE no final!\n"
    "Se o IP da impressora for 192.168.10.50, você NÃO PODE colocar 50 no final aqui.\n"
    "Coloque um número diferente perto dele, como 192.168.10.51."
)
lbl_aviso = tk.Label(root, text=texto_explicacao, font=("Arial", 8, "italic"), bg="#FFF3CD", fg="#856404", justify="left", wraplength=430, relief="solid", bd=1, padx=8, pady=6)
lbl_aviso.pack(fill="x", pady=(0, 10))

# Campo 4
tk.Label(root, text="4. NOVO IP secundário (ex: 192.168.10.51):").pack(anchor="w")
entry_novo_ip = tk.Entry(root, width=55)
entry_novo_ip.insert(0, cache_dados.get("novo_ip", "192.168."))
entry_novo_ip.pack(pady=(0, 8))

# Campo 5
tk.Label(root, text="5. Máscara de sub-rede nova (ex: 255.255.255.0):").pack(anchor="w")
entry_mascara = tk.Entry(root, width=55)
entry_mascara.insert(0, cache_dados.get("mascara", "255.255.255.0"))
entry_mascara.pack(pady=(0, 8))

# Campo 6
tk.Label(root, text="6. NOVO Gateway secundário (ex: 192.168.10.1):").pack(anchor="w")
entry_novo_gw = tk.Entry(root, width=55)
entry_novo_gw.insert(0, cache_dados.get("novo_gw", "192.168."))
entry_novo_gw.pack(pady=(0, 15))

# Botões
frame_botoes = tk.Frame(root)
frame_botoes.pack(fill="x")

btn_aplicar = tk.Button(frame_botoes, text="Aplicar Configuração", bg="lightgreen", font=("Arial", 10, "bold"), command=aplicar_config)
btn_aplicar.pack(side="left", expand=True, fill="x", padx=(0, 5), ipady=5)

btn_restaurar = tk.Button(frame_botoes, text="Restaurar DHCP (Sair)", bg="lightcoral", font=("Arial", 10, "bold"), command=restaurar_dhcp)
btn_restaurar.pack(side="right", expand=True, fill="x", padx=(5, 0), ipady=5)

root.mainloop()
