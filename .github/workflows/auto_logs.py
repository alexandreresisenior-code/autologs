import os
import csv
import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. Configurações de pastas e downloads
pasta_atual = os.getcwd()

config_edge = Options()
config_edge.add_argument("--headless")  # Roda oculto em segundo plano
config_edge.add_experimental_option("prefs", {
    "download.default_directory": pasta_atual,
    "download.prompt_for_download": False,
    "directory_upgrade": True
})

# 2. Leitura do arquivo de credenciais (credenciais.txt)
# Formato esperado no TXT (uma informação por linha):
# URL_DE_LOGIN
# SEU_USUARIO
# SUA_SENHA
try:
    with open('credenciais.txt', 'r', encoding='utf-8') as f:
        linhas = [linha.strip() for list_linha in f if (linha := list_linha.strip())]
    url_login = linhas[0]
    usuario = linhas[1]
    senha = linhas[2]
except Exception as e:
    print(f"Erro ao ler 'credenciais.txt': {e}")
    input("Pressione Enter para sair...")
    exit()

# 3. Inicia o Navegador
print("Iniciando navegador...")
driver = webdriver.Edge(options=config_edge)
wait = WebDriverWait(driver, 15) # Tempo máximo de espera para elementos carregarem

try:
    # 4. Realiza o Login
    print(f"Acessando página de login: {url_login}")
    driver.get(url_login)
    
    # --- AJUSTE OS SELETORES ABAIXO CONFORME O SEU SITE ---
    print("Preenchendo dados de acesso...")
    wait.until(EC.presence_of_element_located((By.ID, "usuario"))).send_keys(usuario)
    driver.find_element(By.ID, "senha").send_keys(senha)
    driver.find_element(By.ID, "btn-enviar").click()
    
    # Aguarda o login concluir (mude o seletor para algo que só exista após o login)
    time.sleep(5) 
    print("Login efetuado com sucesso!")

    # 5. Leitura dos UUIDs e downloads em massa
    if not os.path.exists('uuids.csv'):
        print("Erro: O arquivo 'uuids.csv' não foi encontrado.")
        driver.quit()
        input("Pressione Enter para sair...")
        exit()

    with open('uuids.csv', 'r', encoding='utf-8') as f_csv:
        leitor_csv = csv.reader(f_csv)
        for linha in leitor_csv:
            if not linha:
                continue
            uuid = linha[0].strip()
            
            # --- AJUSTE A URL DO LOG ABAIXO ---
            # Exemplo: se a url for 'https://sistema.com/log/1234-uuid-5678'
            # Modifique a base da URL conforme a estrutura real do seu sistema.
            url_log = f"https://seu-sistema.com/log/{uuid}" 
            
            print(f"Acessando log da UUID: {uuid}")
            driver.get(url_log)
            
            try:
                # --- AJUSTE O SELETOR DO BOTÃO DE EXCEL ABAIXO ---
                # Aguarda o botão de descarregar Excel estar clicável na página
                print(f"Localizando botão de download para {uuid}...")
                botao_excel = wait.until(EC.element_to_be_clickable((By.ID, "botao-download-excel")))
                botao_excel.click()
                
                print(f"Download solicitado para UUID: {uuid}")
                time.sleep(2) # Pequena pausa entre requisições para evitar bloqueios
                
            except Exception as e_loop:
                print(f"Não foi possível descarregar o log da UUID {uuid}. Erro: {e_loop}")

    # Aguarda os últimos downloads finalizarem antes de fechar o navegador
    print("Aguardando finalização dos downloads...")
    time.sleep(7)
    print("Processo concluído com sucesso!")

except Exception as e:
    print(f"Ocorreu um erro geral no processo: {e}")

finally:
    driver.quit()
    input("\nPressione Enter para fechar...")
