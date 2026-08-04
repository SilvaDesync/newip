import ctypes
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

def aplicar_config():
    adaptador = entry_adaptador.get()
    ip_atual = entry_ip_atual.get()
    gw_atual = entry_gw_atual.get()
    novo_ip = entry_novo_ip.get()
    mascara = entry_mascara.get()
    novo_gw = entry_novo_gw.get()

    if not all([adaptador, ip_atual, gw_atual, novo_ip, mascara, novo_gw]):
        messagebox.showwarning("Aviso", "Por favor, preencha todos os campos!")
        return

    try:
        cmd1 = f'netsh interface ipv4 set address name="{adaptador}" static {ip_atual} {mascara} {gw_atual} 1'
        subprocess.run(cmd1, shell=True, check=True, capture_output=True)

        cmd2 = f'netsh interface ipv4 add address name="{adaptador}" {novo_ip} {mascara}'
        subprocess.run(cmd2, shell=True, check=True, capture_output=True)

        cmd3 = f'netsh interface ipv4 add address name="{adaptador}" gateway={novo_gw} gwmetric=2'
        subprocess.run(cmd3, shell=True, check=True, capture_output=True)

        messagebox.showinfo("Sucesso", "REDE CONFIGURADA COM SUCESSO!\nA rede do cliente e a impressora já estão ativas.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Erro", f"Falha ao aplicar configurações:\n{e.stderr.decode('latin-1', errors='ignore')}")

def restaurar_dhcp():
    adaptador = entry_adaptador.get()
    if not adaptador:
        messagebox.showwarning("Aviso", "O campo 'Nome do Adaptador' precisa estar preenchido para restaurar!")
        return

    try:
        cmd1 = f'netsh interface ipv4 set address name="{adaptador}" source=dhcp'
        subprocess.run(cmd1, shell=True, check=True, capture_output=True)

        cmd2 = f'netsh interface ipv4 set dns name="{adaptador}" source=dhcp'
        subprocess.run(cmd2, shell=True, check=True, capture_output=True)

        messagebox.showinfo("Sucesso", "Rede restaurada com sucesso para DHCP automático!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Erro", f"Falha ao restaurar DHCP:\n{e.stderr.decode('latin-1', errors='ignore')}")

root = tk.Tk()
root.title("Configurador de Rede - Fluxo Contínuo")
root.geometry("450x520")
root.resizable(False, False)
root.configure(padx=20, pady=15)

tk.Label(root, text="PASSO 1: CONFIGURAÇÃO DE IP + IMPRESSORA", font=("Arial", 11, "bold")).pack(pady=(0, 10))

tk.Label(root, text="1. Nome exato do adaptador (ex: Wi-Fi ou Ethernet):").pack(anchor="w")
entry_adaptador = tk.Entry(root, width=50)
entry_adaptador.pack(pady=(0, 8))

tk.Label(root, text="2. Seu IP Principal ATUAL:").pack(anchor="w")
entry_ip_atual = tk.Entry(root, width=50)
entry_ip_atual.pack(pady=(0, 8))

tk.Label(root, text="3. Seu Gateway ATUAL:").pack(anchor="w")
entry_gw_atual = tk.Entry(root, width=50)
entry_gw_atual.pack(pady=(0, 15))

tk.Label(root, text="DADOS DA NOVA REDE (Impressora)", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))

tk.Label(root, text="4. NOVO IP secundário (ex: 192.168.10.100):").pack(anchor="w")
entry_novo_ip = tk.Entry(root, width=50)
entry_novo_ip.pack(pady=(0, 8))

tk.Label(root, text="5. Máscara de sub-rede nova (ex: 255.255.255.0):").pack(anchor="w")
entry_mascara = tk.Entry(root, width=50)
entry_mascara.pack(pady=(0, 8))

tk.Label(root, text="6. NOVO Gateway secundário (ex: 192.168.10.1):").pack(anchor="w")
entry_novo_gw = tk.Entry(root, width=50)
entry_novo_gw.pack(pady=(0, 15))

frame_botoes = tk.Frame(root)
frame_botoes.pack(fill="x")

btn_aplicar = tk.Button(frame_botoes, text="Aplicar Configuração", bg="lightgreen", font=("Arial", 10, "bold"), command=aplicar_config)
btn_aplicar.pack(side="left", expand=True, fill="x", padx=(0, 5), ipady=5)

btn_restaurar = tk.Button(frame_botoes, text="Restaurar DHCP (Sair)", bg="lightcoral", font=("Arial", 10, "bold"), command=restaurar_dhcp)
btn_restaurar.pack(side="right", expand=True, fill="x", padx=(5, 0), ipady=5)

root.mainloop()
