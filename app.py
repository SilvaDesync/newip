import ctypes
import sys
import subprocess
import json
import os
import re
import winreg
import customtkinter as ctk
from tkinter import messagebox

CACHE_FILE = "config_cache.json"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ctk.set_appearance_mode("Dark")
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
    valor = str(valor).strip()
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
        btn_spoiler.configure(text="▶ 🛠️ Exibir Todas as Configurações de Rede")
        spoiler_aberto = False
    else:
        frame_spoiler.pack(fill="x", pady=(0, 15), before=btn_aplicar)
        btn_spoiler.configure(text="▼ 🛠️ Ocultar Configurações Avançadas")
        spoiler_aberto = True

def aplicar_config():
    adaptador_raw = entry_adaptador.get()
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
        res1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True)
        if res1.returncode != 0:
            raise Exception(f"Passo 1 (Fixar IP):\n{res1.stderr or res1.stdout}")

        cmd2 = f'netsh interface ipv4 add address name="{adaptador}" {novo_ip_real} {mascara}'
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
    subprocess.run(f'powershell -Command "Remove-Printer -Name \'{target}\' -ErrorAction SilentlyContinue"', shell=True)
    subprocess.run(f'rundll32 printui.dll,PrintUIEntry /dl /n "{target}" /q', shell=True)
    subprocess.run('net stop spooler', shell=True)
    subprocess.run('reg export "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Print" "C:\\BackupPrint.reg" /y', shell=True)
    
    reg_paths = [
        f'HKLM\\SYSTEM\\CurrentControlSet\\Control\\Print\\Printers\\{target}',
        f'HKLM\\SYSTEM\\CurrentControlSet\\Control\\Print\\Environments\\Windows x64\\Drivers\\Version-3\\{target}',
        f'HKLM\\SYSTEM\\CurrentControlSet\\Control\\Print\\Environments\\Windows x64\\Drivers\\Version-4\\{target}',
        f'HKLM\\SYSTEM\\CurrentControlSet\\Control\\Print\\Environments\\Windows NT x86\\Drivers\\Version-3\\{target}',
        f'HKLM\\SYSTEM\\CurrentControlSet\\Control\\Print\\Environments\\Windows NT x86\\Drivers\\Version-4\\{target}'
    ]
    for path in reg_paths:
        subprocess.run(f'reg delete "{path}" /f', shell=True)

    vendor = target.split(' ')[0].replace('-', '')
    ps_cmd_uninstall = (
        f"$vendor = '{vendor}';"
        f"Get-ChildItem -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall', 'HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall' | "
        f"Get-ItemProperty | Where-Object {{ $_.DisplayName -like \"*$vendor*\" -or $_.DisplayName -like \"*{target}*\" -or $_.DisplayName -like '*APD*' -or $_.DisplayName -like '*POS Printer*' }} | "
        f"Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
    )
    subprocess.run(f'powershell -Command "{ps_cmd_uninstall}"', shell=True)

    ps_cmd_folders = (
        f"$vendor = '{vendor}';"
        f"Remove-Item -Path \"HKLM:\\SOFTWARE\\$vendor\", \"HKLM:\\SOFTWARE\\WOW6432Node\\$vendor\", 'HKLM:\\SOFTWARE\\EPSON', 'HKLM:\\SOFTWARE\\WOW6432Node\\EPSON', 'HKLM:\\SOFTWARE\\POS Printer Driver' -Recurse -Force -ErrorAction SilentlyContinue;"
        f"Remove-Item -Path \"C:\\*$vendor*\", 'C:\\POS Printer Driver*', 'C:\\Program Files\\POS Printer Driver*', 'C:\\Program Files (x86)\\POS Printer Driver*' -Recurse -Force -ErrorAction SilentlyContinue"
    )
    subprocess.run(f'powershell -Command "{ps_cmd_folders}"', shell=True)

    subprocess.run('del /Q /F /S "%systemroot%\\System32\\spool\\PRINTERS\\*.*"', shell=True)
    subprocess.run('net start spooler', shell=True)

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
    win.grab_set()

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

    btn_um = ctk.CTkButton(win, text="Remover Selecionado", fg_color="#e67e22", hover_color="#d35400", command=confirmar_remover_um)
    btn_um.pack(fill="x", padx=15, pady=(0, 5))

    btn_todos = ctk.CTkButton(win, text="[ EXCLUIR TODOS OS ITENS ]", fg_color="#c0392b", hover_color="#a93226", command=confirmar_remover_todos)
    btn_todos.pack(fill="x", padx=15, pady=(0, 15))


cache_dados = carregar_cache()
auto_adaptador, auto_ip, auto_gw = detectar_rede_automatica_cmd()

# --- INTERFACE MODERNA DARK ---
root = ctk.CTk()
root.title("Configurador de Rede - Fluxo Contínuo")
root.geometry("500x480")
root.resizable(False, False)
root.configure(fg_color="#18191c")

icon_file = resource_path("icon.ico")
if os.path.exists(icon_file):
    root.iconbitmap(icon_file)

frame = ctk.CTkScrollableFrame(root, corner_radius=15, fg_color="#1e1f22")
frame.pack(fill="both", expand=True, padx=12, pady=12)

lbl_titulo = ctk.CTkLabel(frame, text="PASSO 1: CONFIGURAÇÃO DE IP + IMPRESSORA", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff")
lbl_titulo.pack(pady=(10, 15))

lbl_4 = ctk.CTkLabel(frame, text="Digite o IP da Impressora:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#dcddde", anchor="w")
lbl_4.pack(fill="x", pady=(0, 2))
entry_novo_ip = ctk.CTkEntry(frame, corner_radius=8, fg_color="#2b2d31", border_color="#383a40", text_color="#ffffff", placeholder_text="Ex: 192.168.10.50")
entry_novo_ip.insert(0, cache_dados.get("novo_ip", "192.168.10.50"))
entry_novo_ip.bind("<KeyRelease>", ao_digitar_novo_ip)
entry_novo_ip.pack(fill="x", pady=(0, 15))

spoiler_aberto = False
btn_spoiler = ctk.CTkButton(
    frame, 
    text="▶ 🛠️ Exibir Todas as Configurações de Rede", 
    fg_color="transparent", 
    text_color="#949ba4",
    hover_color="#2b2d31",
    anchor="w",
    command=alternar_spoiler
)
btn_spoiler.pack(fill="x", pady=(0, 10))

frame_spoiler = ctk.CTkFrame(frame, corner_radius=10, fg_color="#2b2d31")

lbl_1 = ctk.CTkLabel(frame_spoiler, text="1. Adaptador (1 para Wi-Fi / 2 para Cabo):", text_color="#dcddde", anchor="w")
lbl_1.pack(fill="x", padx=10, pady=(10, 2))
entry_adaptador = ctk.CTkEntry(frame_spoiler, corner_radius=8, fg_color="#1e1f22", border_color="#383a40", text_color="#ffffff")
entry_adaptador.insert(0, auto_adaptador or cache_dados.get("adaptador", ""))
entry_adaptador.pack(fill="x", padx=10, pady=(0, 10))

lbl_2 = ctk.CTkLabel(frame_spoiler, text="2. Seu IP Principal ATUAL:", text_color="#dcddde", anchor="w")
lbl_2.pack(fill="x", padx=10, pady=(0, 2))
entry_ip_atual = ctk.CTkEntry(frame_spoiler, corner_radius=8, fg_color="#1e1f22", border_color="#383a40", text_color="#ffffff")
entry_ip_atual.insert(0, auto_ip or cache_dados.get("ip_atual", "192.168."))
entry_ip_atual.pack(fill="x", padx=10, pady=(0, 10))

lbl_3 = ctk.CTkLabel(frame_spoiler, text="3. Seu Gateway ATUAL:", text_color="#dcddde", anchor="w")
lbl_3.pack(fill="x", padx=10, pady=(0, 2))
entry_gw_atual = ctk.CTkEntry(frame_spoiler, corner_radius=8, fg_color="#1e1f22", border_color="#383a40", text_color="#ffffff")
entry_gw_atual.insert(0, auto_gw or cache_dados.get("gw_atual", "192.168."))
entry_gw_atual.pack(fill="x", padx=10, pady=(0, 10))

lbl_5 = ctk.CTkLabel(frame_spoiler, text="5. Máscara de sub-rede nova:", text_color="#dcddde", anchor="w")
lbl_5.pack(fill="x", padx=10, pady=(0, 2))
entry_mascara = ctk.CTkEntry(frame_spoiler, corner_radius=8, fg_color="#1e1f22", border_color="#383a40", text_color="#ffffff")
entry_mascara.insert(0, cache_dados.get("mascara", "255.255.255.0"))
entry_mascara.pack(fill="x", padx=10, pady=(0, 10))

lbl_6 = ctk.CTkLabel(frame_spoiler, text="6. NOVO Gateway secundário (Auto-preenchido):", text_color="#dcddde", anchor="w")
lbl_6.pack(fill="x", padx=10, pady=(0, 2))
entry_novo_gw = ctk.CTkEntry(frame_spoiler, corner_radius=8, fg_color="#1e1f22", border_color="#383a40", text_color="#ffffff")
entry_novo_gw.insert(0, cache_dados.get("novo_gw", "192.168.10.1"))
entry_novo_gw.pack(fill="x", padx=10, pady=(0, 10))

# BOTÕES DE AÇÃO
btn_aplicar = ctk.CTkButton(
    frame, 
    text="Aplicar Configuração", 
    font=ctk.CTkFont(size=12, weight="bold"),
    fg_color="#23a55a", 
    hover_color="#1d8a4b", 
    corner_radius=10,
    height=38,
    command=aplicar_config
)
btn_aplicar.pack(fill="x", pady=(5, 8))

btn_limpeza = ctk.CTkButton(
    frame, 
    text="🧹 Limpeza Total de Impressoras e Drivers", 
    font=ctk.CTkFont(size=12, weight="bold"),
    fg_color="#f0b232", 
    hover_color="#c89326", 
    text_color="#000000",
    corner_radius=10,
    height=38,
    command=abrir_janela_limpeza
)
btn_limpeza.pack(fill="x", pady=(0, 8))

btn_restaurar = ctk.CTkButton(
    frame, 
    text="Restaurar DHCP (Sair)", 
    font=ctk.CTkFont(size=12, weight="bold"),
    fg_color="#f23f43", 
    hover_color="#d03135", 
    corner_radius=10,
    height=38,
    command=restaurar_dhcp
)
btn_restaurar.pack(fill="x", pady=(0, 12))

# PAINEL DE INSTRUÇÕES
frame_instrucoes = ctk.CTkFrame(frame, corner_radius=10, fg_color="#2b2d31")
frame_instrucoes.pack(fill="x", pady=(0, 5))

lbl_inst_titulo = ctk.CTkLabel(
    frame_instrucoes, 
    text="📌 INSTRUÇÕES E DICAS DE USO", 
    font=ctk.CTkFont(size=12, weight="bold"),
    text_color="#ffffff"
)
lbl_inst_titulo.pack(anchor="w", padx=12, pady=(10, 5))

texto_instrucoes = (
    "1. Digite o endereço IP da impressora no campo acima.\n"
    "2. Clique em 'Aplicar Configuração' para autorizar a comunicação.\n"
    "3. Use 'Limpeza Total' para remover drivers antigos corrompidos.\n"
    "4. Se mudar de rede Wi-Fi/Cabo, clique em 'Restaurar DHCP (Sair)'.\n"
    "5. Expanda as configurações avançadas caso precise de ajustes manuais."
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
