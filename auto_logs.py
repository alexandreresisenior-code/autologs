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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. Configurações Iniciais e Diretorias
pasta_atual = os.getcwd()
data_atual = datetime.now().strftime("%d-%m-%Y")
nome_pasta_logs = f'Logs_{data_atual}'

# Cria a pasta de destino do dia se não existir
if not os.path.exists(nome_pasta_logs):
    os.mkdir(nome_pasta_logs)

# Limpeza de resíduos de execuções anteriores
if os.path.exists('data.xlsx'):
    os.remove('data.xlsx')

# 2. Configuração do Edge para rodar em Segundo Plano (Headless)
config_edge = Options()
config_edge.add_argument("--headless=new")
config_edge.add_argument("--disable-gpu")
config_edge.add_argument("--window-size=1920,1080")
config_edge.add_argument("--disable-infobars")
config_edge.add_argument("--no-sandbox")

# 3. Leitura do ficheiro de configuração (acesso.txt)
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
    print("Erro: 'acesso.txt' não contém todas as credenciais necessárias (Site, Username, Password).")
    exit()

# 4. Inicialização do Selenium para Captura do Token de Sessão (loginId)
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
    print(f"Aceder à página de autenticação: {url_visu}")
    driver.get(url_visu)
    time.sleep(3)

    # Clique robusto no botão 'Manual Login'
    print("A selecionar o modo 'Manual Login'...")
    botao_manual = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'userButton') and contains(text(), 'Manual Login')]")))
    driver.execute_script("arguments[0].click();", botao_manual)
    time.sleep(4)

    # Preenchimento de Credenciais
    print("A introduzir as credenciais...")
    campo_user = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='text']")))
    campo_user.clear()
    campo_user.send_keys(username)

    campo_pass = driver.find_element(By.XPATH, "//input[@type='password']")
    campo_pass.clear()
    campo_pass.send_keys(password)

    # Submeter o Login
    print("A efetuar login...")
    botao_confirmar = driver.find_element(By.XPATH, "//*[text()='OK' or text()='Ok' or text()='Log-In']")
    driver.execute_script("arguments[0].click();", botao_confirmar)
    time.sleep(6)

    # Captura Dinâmica do loginId através da URL
    url_pos_login = driver.current_url
    if "loginId=" in url_pos_login:
        id_login = url_pos_login.split("loginId=")[1].split("&")[0]
        print(f"Token de Sessão obtido com sucesso: {id_login}")
    else:
        print("Erro Crítico: Não foi possível capturar o loginId da URL pós-login.")
        driver.quit()
        exit()

    # O navegador já cumpriu o seu papel, podemos fechá-lo!
    driver.quit()

    # 5. Download em Massa e Processamento de Dados via API (Requests + Pandas)
    if not os.path.exists('uuids.csv'):
        print("Erro: O ficheiro 'uuids.csv' não foi encontrado.")
        exit()

    print("\nA iniciar a extração de dados através da API...")
    with open('uuids.csv', newline='', encoding='utf-8') as csvfile:
        # Deteta se o separador é ponto e vírgula ou vírgula automaticamente
        reader = csv.reader(csvfile, delimiter=';')
        
        for row in reader:
            if not row or len(row) < 2:
                continue
            uuid = row[0].strip()
            quarto = row[1].strip()
            
            # Constrói o endpoint correto da API do CODESYS
            url_api = f"http://{site}/webif/gaobjcgi?action=jobCommand&uuid={uuid}&cmd=getLog&loginId={id_login}"
            
            print(f"A processar: {quarto} (UUID: {uuid})...")
            try:
                response = requests.get(url_api, timeout=15)
                
                if response.status_code == 200:
                    json_data = response.json()
                    
                    if 'history' in json_data and json_data['history']:
                        # Normaliza o JSON para DataFrame do Pandas
                        df = pd.json_normalize(json_data['history'])
                        
                        # Converte timestamp UNIX (ms) para data legível
                        if 'timestamp' in df.columns:
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce').dt.tz_localize(None)
                        
                        # Mapeamento de Status (Substituição de IDs numéricos para Texto)
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
                        
                        # Nome provisório do ficheiro
                        ficheiro_temporario = 'data.xlsx'
                        df.to_excel(ficheiro_temporario, index=False)
                        
                        # Formatação Visual e Cores com Openpyxl
                        nome_ficheiro_final = os.path.join(nome_pasta_logs, f'{quarto}_{data_current=}.xlsx'.replace('data_current=', data_atual))
                        
                        # Se já existir um ficheiro com esse nome, remove para evitar conflitos
                        if os.path.exists(nome_ficheiro_final):
                            os.remove(nome_ficheiro_final)
                            
                        os.rename(ficheiro_temporario, nome_ficheiro_final)
                        
                        # Aplicar as cores nas células do Excel
                        wb = load_workbook(nome_ficheiro_final)
                        ws = wb.active
                        
                        # Dicionário de cores (Hexadecimal)
                        cores_status = {
                            "OK": "66ff66",                           # Verde
                            "FAULT": "ff6666",                        # Vermelho
                            "CONFIRMED": "ffff66",                    # Amarelo
                            "OK (prev. fault unconfirmed)": "6666ff"  # Azul
                        }
                        
                        for row_cells in ws.iter_rows(min_row=2):
                            for cell in row_cells:
                                if cell.value in cores_status:
                                    cor_hex = cores_status[cell.value]
                                    cell.fill = PatternFill(start_color=cor_hex, end_color=cor_hex, fill_type="solid")
                        
                        wb.save(nome_ficheiro_final)
                        print(f" -> {quarto} - CONCLUÍDO COM SUCESSO")
                    else:
                        print(f" -> {quarto} - Sem dados de histórico disponíveis.")
                else:
                    print(f" -> {quarto} - Falha na API (Status Code: {response.status_code})")
                    
            except Exception as e_loop:
                print(f" -> Erro ao processar o quarto {quarto}: {e_loop}")

    print(f"\nTodo o processo foi concluído! Os ficheiros estão na pasta: {nome_pasta_logs}")

except Exception as e_geral:
    print(f"\nOcorreu um erro geral no sistema: {e_geral}")
