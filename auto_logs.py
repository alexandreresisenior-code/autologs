import os
import csv
import time
import glob
import re
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. Configurações de pastas e downloads em segundo plano (Headless)
pasta_atual = os.getcwd()

config_edge = Options()
config_edge.add_argument("--headless=new")
config_edge.add_argument("--disable-gpu")
config_edge.add_argument("--window-size=1920,1080")
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
    senha = linhas[2]
except Exception as e:
    print(f"Erro ao ler 'credenciais.txt': {e}")
    input("\nPressione Enter para sair...")
    exit()

# 3. Inicia o Navegador Edge
print("Iniciando navegador em segundo plano...")
try:
    servico_edge = Service()
    driver = webdriver.Edge(service=servico_edge, options=config_edge)
    
    driver.execute_cdp_cmd("Page.setDownloadBehavior", {
        "behavior": "allow",
        "downloadPath": pasta_atual
    })
except Exception as err_nav:
    print(f"\n--- ERRO AO INICIAR O EDGE ---\n{err_nav}\n-----------------------------------")
    input("\nPressione Enter para fechar...")
    exit()

wait = WebDriverWait(driver, 15)

try:
    # 4. Realiza o Login dinâmico no WebVisu / CODESYS
    print(f"Acessando página de login: {url_login}")
    driver.get(url_login)
    
    print("Aguardando e clicando no botão 'Manual Login'...")
    try:
        botao_manual = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Manual') or contains(text(), 'Login') or @type='button']")))
        driver.execute_script("arguments[0].click();", botao_manual)
        print("Botão 'Manual Login' clicado com sucesso. Aguardando formulário...")
        time.sleep(2)
    except Exception as e_btn:
        print(f"Aviso ao tentar clicar no botão inicial (pode já estar aberto): {e_btn}")

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

    print("Confirmando o login...")
    try:
        botao_confirmar = driver.find_element(By.XPATH, "//*[text()='OK' or text()='Ok' or text()='Log-In' or @type='submit']")
        botao_confirmar.click()
    except Exception:
        from selenium.webdriver.common.keys import Keys
        campo_senha.send_keys(Keys.ENTER)

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

    # 5. Leitura dos UUIDs e downloads em massa
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
            
            print(f"\nAcessando log da UUID: {uuid}")
            driver.get(url_log)
            time.sleep(2)
            
            # --- CAPTURA SEGURA DO NOME NO CAMPO VALUES DA TABELA ---
            nome_final_ficheiro = uuid
            try:
                elemento_valor = driver.find_element(By.XPATH, "//th[contains(text(), 'Values')]/following::td[1]")
                texto_campo = elemento_valor.text.strip()
                if not texto_campo:
                    elemento_valor = driver.find_element(By.XPATH, "//th[contains(text(), 'Values')]/ancestor::table//tr[2]/td[position()=2]")
                    texto_campo = elemento_valor.text.strip()
                
                if texto_campo:
                    nome_limpo = re.sub(r'[\\/*?:"<>|]', "", texto_campo).replace(" ", "_")
                    if nome_limpo:
                        nome_final_ficheiro = nome_limpo
                        print(f"Nome identificado na tabela: {nome_final_ficheiro}")
            except Exception:
                print(f"Aviso: Não encontrou o campo 'Values'. Usando UUID.")

            try:
                arquivos_antes = set(glob.glob(os.path.join(pasta_atual, "*")))
                
                print(f"Aguardando botão 'download' ficar visível...")
                botao_download = wait.until(EC.element_to_be_clickable((By.ID, "download")))
                
                driver.execute_script("arguments[0].click();", botao_download)
                print(f"Download solicitado...")
                
                arquivo_detectado = None
                for _ in range(10):
                    time.sleep(1)
                    arquivos_depois = set(glob.glob(os.path.join(pasta_atual, "*")))
                    novos_arquivos = arquivos_depois - arquivos_antes
                    novos_validos = [f for f in novos_arquivos if not f.endswith('.crdownload') and not f.endswith('.tmp')]
                    if novos_validos:
                        arquivo_detectado = novos_validos[0]
                        break
                
                if arquivo_detectado and os.path.exists(arquivo_detectado):
                    extensao = os.path.splitext(arquivo_detectado)[1]
                    if not extensao:
                        extensao = ".txt"
                        
                    novo_nome = os.path.join(pasta_atual, f"{nome_final_ficheiro}{extensao}")
                    if os.path.exists(novo_nome):
                        os.remove(novo_nome)
                        
                    os.rename(arquivo_detectado, novo_nome)
                    print(f"Ficheiro guardado como: {nome_final_ficheiro}{extensao}")
                else:
                    print(f"Aviso: O download demorou a responder.")
                
            except Exception as e_loop:
                print(f"Não foi possível processar a UUID {uuid}. Erro: {e_loop}")

    print("\nProcesso concluído com sucesso!")

except Exception as e:
    print(f"\nOcorreu um erro geral no processo: {e}")

finally:
    driver.quit()
    input("\nProcesso finalizado. Pressione Enter para fechar a janela...")
