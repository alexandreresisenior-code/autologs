import os
import csv
import time
import re
import requests
import pandas as pd
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. Configurações Iniciais e Diretorias
pasta_atual = os.getcwd()
data_atual = datetime.now().strftime("%d-%m-%Y")
nome_pasta_logs = f'Logs_{data_atual}'

if not os.path.exists(nome_pasta_logs):
    os.mkdir(nome_pasta_logs)

if os.path.exists('data.xlsx'):
    os.remove('data.xlsx')

# 2. Configuração do Edge Headless (Segundo Plano)
config_edge = Options()
config_edge.add_argument("--headless=new")
config_edge.add_argument("--disable-gpu")
config_edge.add_argument("--window-size=1920,1080")
config_edge.add_argument("--disable-infobars")
config_edge.add_argument("--no-sandbox")

# 3. Leitura das credenciais (acesso.txt)
site, username, password = None, None, None
try:
    with open('acesso.txt', 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.split("--")
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip()
                if key == "Site":
                    site = val
                elif key == "Username":
                    username = val
                elif key == "Password":
                    password = val
except Exception as e:
    print(f"Erro ao ler o ficheiro 'acesso.txt': {e}")
    exit()

if not all([site, username, password]):
    print("Erro: 'acesso.txt' incompleto. Certifique-se de ter Site, Username e Password definidos.")
    exit()

# 4. Autenticação no Navegador
print("A iniciar o navegador em segundo plano para autenticação...")
try:
    servico_edge = Service()
    driver = webdriver.Edge(service=servico_edge, options=config_edge)
except Exception as err_nav:
    print(f"Erro ao iniciar o Edge: {err_nav}")
    exit()

wait = WebDriverWait(driver, 15)

try:
    url_visu = f"http://{site}/web.visu/"
    print(f"Aceder à página: {url_visu}")
    driver.get(url_visu)
    time.sleep(3)

    print("A selecionar o modo 'Manual Login'...")
    botao_manual = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'userButton') and contains(text(), 'Manual Login')]")))
    driver.execute_script("arguments[0].click();", botao_manual)
    time.sleep(4)

    print("A introduzir as credenciais...")
    campo_user = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='text'] | //form//input[1]")))
    campo_user.clear()
    campo_user.send_keys(username)

    campo_pass = driver.find_element(By.XPATH, "//input[@type='password'] | //form//input[2]")
    campo_pass.clear()
    campo_pass.send_keys(password)

    print("A submeter o formulário de login...")
    try:
        # Alvo exato na div[4] interna do formulário (vinda do seu script original)
        botao_confirmar = driver.find_element(By.XPATH, "//form/div[4] | //div[contains(@class, 'button') and text()='OK']")
        driver.execute_script("arguments[0].click();", botao_confirmar)
    except Exception:
        campo_pass.send_keys(Keys.ENTER)

    # ESPERA DINÂMICA: Aguarda até 25 segundos para que a URL mude e contenha o 'loginId='
    print("A aguardar pela validação das credenciais e geração do Token (loginId)...")
    try:
        WebDriverWait(driver, 25).until(EC.url_contains("loginId="))
    except Exception:
        print("\n[Aviso] O tempo limite de espera expirou. A verificar URL obtida...")

    url_pos_login = driver.current_url
    
    if "loginId=" in url_pos_login:
        id_login = url_pos_login.split("loginId=")[1].split("&")[0]
        print(f"Token de Sessão (loginId) obtido com sucesso: {id_login}")
    else:
        print(f"\nErro Crítico: Não foi possível capturar o loginId.")
        print(f"URL Atual do navegador: {url_pos_login}")
        print("Verifique se as credenciais no 'acesso.txt' estão corretas.")
        driver.quit()
        exit()

    # Fechar o navegador pois o token já foi guardado
    driver.quit()

    # 5. Processamento dos UUIDs via API (Requests + Pandas)
    if not os.path.exists('uuids.csv'):
        print("Erro: O ficheiro 'uuids.csv' não foi encontrado.")
        exit()

    print("\nA iniciar a extração de dados através da API...")
    with open('uuids.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        
        for row in reader:
            if not row or len(row) < 2:
                continue
            uuid = row[0].strip()
            quarto = row[1].strip()
            
            url_api = f"http://{site}/webif/gaobjcgi?action=jobCommand&uuid={uuid}&cmd=getLog&loginId={id_login}"
            print(f"A processar: {quarto}...")
            
            try:
                response = requests.get(url_api, timeout=15)
                if response.status_code == 200:
                    json_data = response.json()
                    
                    if 'history' in json_data and json_data['history']:
                        df = pd.json_normalize(json_data['history'])
                        
                        if 'timestamp' in df.columns:
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce').dt.tz_localize(None)
                        
                        status_map = {
                            0: 'OK',
                            1: 'FAULT',
                            2: 'CONFIRMED',
                            3: 'OK (prev. fault unconfirmed)'
                        }
                        
                        if 'statusFrom' in df.columns:
                            df['statusFrom'] = df['statusFrom'].map(status_map).fillna(df['statusFrom'])
                        if 'statusTo' in df.columns:
                            df['statusTo'] = df['statusTo'].map(status_map).fillna(df['statusTo'])
                        
                        ficheiro_temporario = 'data.xlsx'
                        df.to_excel(ficheiro_temporario, index=False)
                        
                        nome_ficheiro_final = os.path.join(nome_pasta_logs, f'{quarto}_{data_atual}.xlsx')
                        
                        if os.path.exists(nome_ficheiro_final):
                            os.remove(nome_ficheiro_final)
                            
                        os.rename(ficheiro_temporario, nome_ficheiro_final)
                        
                        # Colorir células
                        wb = load_workbook(nome_ficheiro_final)
                        ws = wb.active
                        
                        cores_status = {
                            "OK": "66ff66",
                            "FAULT": "ff6666",
                            "CONFIRMED": "ffff66",
                            "OK (prev. fault unconfirmed)": "6666ff"
                        }
                        
                        for row_cells in ws.iter_rows(min_row=2):
                            for cell in row_cells:
                                if cell.value in cores_status:
                                    cor_hex = cores_status[cell.value]
                                    cell.fill = PatternFill(start_color=cor_hex, end_color=cor_hex, fill_type="solid")
                        
                        wb.save(nome_ficheiro_final)
                        print(f" -> {quarto} - CONCLUÍDO")
                    else:
                        print(f" -> {quarto} - Sem dados disponíveis.")
                else:
                    print(f" -> {quarto} - Falha na API (Status: {response.status_code})")
            except Exception as e_loop:
                print(f" -> Erro no quarto {quarto}: {e_loop}")

    print(f"\nProcesso concluído! Ficheiros guardados em: {nome_pasta_logs}")

except Exception as e_geral:
    print(f"\nOcorreu um erro geral no sistema: {e_geral}")
