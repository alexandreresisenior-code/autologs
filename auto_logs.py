import os
import csv
import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. Configurações de pastas e downloads
pasta_atual = os.getcwd()

config_edge = Options()
config_edge.add_argument("--start-maximized")
config_edge.add_experimental_option("prefs", {
    "download.default_directory": pasta_atual,
    "download.prompt_for_download": False,
    "directory_upgrade": True
})

# 2. Leitura do arquivo de credenciais (credenciais.txt)
try:
    with open('credenciais.txt', 'r', encoding='utf-8') as f:
        linhas = [linha.strip() for list_linha in f if (linha := list_linha.strip())]
    url_login = linhas[0]
    usuario = linhas[1]
    senha = líneas[2]
except Exception as e:
    print(f"Erro ao ler 'credenciais.txt': {e}")
    input("\nPressione Enter para sair...")
    exit()

# 3. Inicia o Navegador Edge com tratamento de exceção
print("Iniciando navegador Microsoft Edge...")
try:
    servico_edge = Service()
    driver = webdriver.Edge(service=servico_edge, options=config_edge)
except Exception as err_nav:
    print(f"\n--- ERRO AO INICIAR O EDGE ---")
    print(err_nav)
    print("-----------------------------------")
    input("\nPressione Enter para fechar...")
    exit()

wait = WebDriverWait(driver, 15)

try:
    # 4. Realiza o Login dinâmico no WebVisu / CODESYS
    print(f"Acessando página de login: {url_login}")
    driver.get(url_login)
    
    # Passo A: Clicar no botão inicial de login (Manual Login)
    print("Aguardando o botão de Login aparecer na tela...")
    try:
        botao_login_inicial = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Login') or contains(text(), 'Manual')]")))
        botao_login_inicial.click()
        print("Botão inicial clicado. Aguardando campos de texto...")
        time.sleep(2)
    except Exception:
        print("Aviso: Não encontrou o botão por texto, tentando prosseguir assumindo que o form já possa estar aberto...")

    # Passo B: Preencher Usuário e Senha
    print("Preenchendo dados de acesso...")
    try:
        campo_usuario = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text']")))
    except Exception:
        campo_usuario = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'User')]/following::input[1]")))
        
    campo_usuario.clear()
    campo_usuario.send_keys(usuario)

    try:
        campo_senha = driver.find_element(By.XPATH, "//input[@type='password']")
    except Exception:
        campo_senha = driver.find_element(By.XPATH, "//*[contains(text(), 'Password')]/following::input[1]")
        
    campo_senha.clear()
    campo_senha.send_keys(senha)

    # Passo C: Clicar no botão 'OK' para confirmar o login
    print("Confirmando o login...")
    try:
        botao_confirmar = driver.find_element(By.XPATH, "//*[text()='OK' or text()='Ok' or text()='Log-In' or @type='submit']")
        botao_confirmar.click()
    except Exception:
        from selenium.webdriver.common.keys import Keys
        campo_senha.send_keys(Keys.ENTER)

    # Aguarda o painel interno carregar após o login
    time.sleep(5) 
    print("Login efetuado com sucesso!")

    # --- CAPTURA DO LOGIN ID DINÂMICO ---
    url_atual = driver.current_url
    print(f"URL após login: {url_atual}")
    
    if "loginId=" in url_atual:
        login_id = url_atual.split("loginId=")[1].split("&")[0]
        print(f"Token de Sessão Detectado: {login_id}")
    else:
        print("Erro crítico: Não foi possível capturar o loginId da URL pós-login.")
        driver.quit()
        input("\nPressione Enter para sair...")
        exit()

    # 5. Leitura dos UUIDs e downloads em massa usando o Token capturado
    if not os.path.exists('uuids.csv'):
        print("Erro: O arquivo 'uuids.csv' não foi encontrado.")
        driver.quit()
        input("\nPressione Enter para sair...")
        exit()

    with open('uuids.csv', 'r', encoding='utf-8') as f_csv:
        leitor_csv = csv.reader(f_csv)
        for linha in leitor_csv:
            if not linha:
                continue
            uuid = linha[0].strip()
            
            url_log = f"http://resisenior.dynip.sapo.pt:8090/webif/StatusNotificationLog.html?uuid={uuid}&loginId={login_id}" 
            
            print(f"Acessando log da UUID: {uuid}")
            driver.get(url_log)
            
            try:
                print(f"Localizando botão de download para {uuid}...")
                botao_excel = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Excel') or contains(text(), 'Export') or contains(@value, 'Excel')]")))
                botao_excel.click()
                print(f"Download solicitado para UUID: {uuid}")
                time.sleep(3)
            except Exception as e_loop:
                print(f"Não foi possível descarregar o log da UUID {uuid}. Erro: {e_loop}")

    print("\nAguardando finalização de todos os downloads...")
    time.sleep(7)
    print("Processo concluído com sucesso!")

except Exception as e:
    print(f"\nOcorreu um erro geral no processo: {e}")

finally:
    driver.quit()
    input("\nProcesso finalizado. Pressione Enter para fechar a janela...")
