@echo off
title Configurador de Rede - Fluxo Continuo
color 0A

:: Testa se esta rodando como Administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ==========================================================
    echo [ERRO] Voce PRECISA executar este script como Administrador!
    echo ==========================================================
    echo.
    echo Clique com o botao direito no arquivo e escolha:
    echo "Executar como Administrador"
    echo.
    pause
    exit /b
)

cls
echo ==========================================================
echo         PASSO 1: CONFIGURACAO DE IP + IMPRESSORA
echo ==========================================================
echo.

:: Coleta manual e direta dos dados para configuracao
set /p "adaptador=1. Nome exato do adaptador (ex: Wi-Fi ou Ethernet - PRECISA DIGITAR IGUAL ESTA NO EX): "
set /p "ip_atual=2. Seu IP Principal ATUAL da internet (ex: CMD>IPCONFIG>IPV4....): "
set /p "gw_atual=3. Seu Gateway ATUAL da internet (CMD>IPCONFIG>GATEWAY....): "
echo.
echo ----------------------------------------------------------
echo Dados da nova rede (Com a faixa de ip igual a da Impressora - o IP após a faixa não pode ser igual):
echo ----------------------------------------------------------
set /p "novo_ip=4. NOVO IP secundario (ex: 192.168.10.100): "
set /p "mascara=5. Mascara de sub-rede nova (ex: 255.255.255.0): "
set /p "novo_gw=6. NOVO Gateway secundario (ex: 192.168.10.1): "

cls
echo ==========================================================
echo                     PREVIEW DA ACAO
echo ==========================================================
echo.
echo Adaptador Selecionado: %adaptador%
echo.
echo [PASSO 1] Vai FIXAR sua internet principal (Desativar DHCP):
echo           IP Principal: %ip_atual%
echo           Mascara:      %mascara%
echo           Gateway:      %gw_atual%
echo.
echo [PASSO 2] Vai ADICIONAR na aba Avancado:
echo           IP Novo:      %novo_ip%
echo           Gateway Novo: %novo_gw%
echo.
echo ==========================================================
echo Pressione ENTER para aplicar a configuracao...
pause >nul

echo.
echo [+] 1/3 - Fixando seu IP principal e desativando o DHCP...
netsh interface ipv4 set address name="%adaptador%" static %ip_atual% %mascara% %gw_atual% 1

echo [+] 2/3 - Adicionando o IP novo na lista...
netsh interface ipv4 add address name="%adaptador%" %novo_ip% %mascara%

echo [+] 3/3 - Forcando a inclusao do novo Gateway na interface visual...
netsh interface ipv4 add address name="%adaptador%" gateway=%novo_gw% gwmetric=2

cls
echo ==========================================================
echo [OK] REDE CONFIGURADA COM SUCESSO!
echo ==========================================================
echo.
echo A rede do cliente e a impressora ja estao ativas.
echo Pode fazer os ajustes necessarios na impressora agora.
echo.
echo ==========================================================
echo      QUANDO TERMINAR O SEU TRABALHO NA IMPRESSORA:
echo ==========================================================
echo.

:AGUARDAR_SAIDA
set "comando="
set /p "comando=Digite SAIR para restaurar o DHCP e finalizar: "

:: Se o usuario digitar qualquer coisa diferente de "sair", ele continua cobrando o comando
if /i "%comando%"=="sair" goto RESTAURAR_DHCP
echo Comando invalido.
echo.
goto AGUARDAR_SAIDA

:RESTAURAR_DHCP
echo.
echo [+] Restaurando IP e Gateway para automatico (DHCP)...
netsh interface ipv4 set address name="%adaptador%" source=dhcp

echo [+] Restaurando o DNS para automatico (DHCP)...
netsh interface ipv4 set dns name="%adaptador%" source=dhcp

echo.
echo ==========================================================
echo [OK] Rede restaurada com sucesso para DHCP automatico!
echo ==========================================================
echo.
pause
exit /b