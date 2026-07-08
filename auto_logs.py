import os
import csv
import time
import re
import requests
import pandas as pd
import traceback  # Para mostrar a linha exata do erro
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

print("=== INICIANDO MODO DEPURAR (DEBUG) ===")

# 1. Configurações Iniciais e Diretorias
pasta_atual = os.getcwd()
data_atual = datetime.now().strftime("%d-%m-%Y")
nome_pasta_logs = f'Logs_{data_atual}'

print(f"[DEBUG] Diretoria atual: {pasta_atual}")
print(f"[DEBUG] Pasta de destino dos logs: {nome_pasta_logs}")

if not os.path.exists(nome_pasta_logs):
    os.mkdir(nome_pasta_logs)
    print(f"[DEBUG] Pasta '{nome_pasta_logs}' criada.")

if os.path.exists('data.xlsx'):
    try:
        os.remove('data.xlsx')
        print("[DEBUG] Ficheiro temporário 'data.xlsx' antigo removido.")
    except Exception as e:
        print(f"[AVISO] Não foi possível remover 'data.xlsx': {e}")

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
    print("[DEBUG] A ler o ficheiro 'acesso.txt'...")
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
    print(f"[DEBUG] Credenciais lidas -> Site: {site}, Username: {username}")
except Exception as e:
    print(f"[ERRO CRÍTICO] Falha ao ler 'acesso.txt': {e}")
    input("\nPressione Enter para sair...")
    exit()

if not all([site, username, password]):
    print("[ERRO CRÍTICO] 'acesso.txt' tem dados em falta.")
    input("\nPressione Enter para sair...")
    exit()

# 4. Autenticação no Navegador
print("\n[DEBUG] A iniciar o Edge em segundo plano...")
try:
    servico_edge = Service()
    driver = webdriver.Edge(service=servico_edge, options=config_edge)
except Exception as err_nav:
    print(f"[ERRO CRÍTICO] Falha ao iniciar o Edge:\n{traceback.format_exc()}")
    input("\nPressione Enter para sair...")
    exit()

wait = WebDriverWait(driver, 15)

try:
    url_visu = f"http://{site}/web.visu/"
    print(f"[DEBUG] A abrir URL de Login: {url_visu}")
    driver.get(url_visu)
    time.sleep(3)

    print("[DEBUG] A clicar em 'Manual Login'...")
    botao_manual = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'userButton') and contains(text(), 'Manual Login')]")))
    driver.execute_script("arguments[0].click();", botao_manual)
    time.sleep(4)

    print("[DEBUG] A preencher credenciais...")
    campo_user = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='text'] | //form//input[1]")))
    campo_user.clear()
    campo_user.send_keys(username)

    campo_pass = driver.find_element(By.XPATH, "//input[@type='password'] | //form//input[2]")
    campo_pass.clear()
    campo_pass.send_keys(password)

    print("[DEBUG] A submeter formulário...")
    try:
        botao_confirmar = driver.find_element(By.XPATH, "//form/div[4] | //div[contains(@class, 'button') and text()='OK']")
        driver.execute_script("arguments[0].click();", botao_confirmar)
    except Exception:
        print("[DEBUG] Botão OK não encontrado via XPath direto, a tentar enviar ENTER...")
        campo_pass.send_keys(Keys.ENTER)

    print("[DEBUG] A aguardar validação do loginId na URL...")
    try:
        WebDriverWait(driver, 25).until(EC.url_contains("loginId="))
    except Exception:
        print("[AVISO] Tempo limite de espera esgotado.")

    url_pos_login = driver.current_url
    print(f"[DEBUG] URL detectada após login: {url_pos_login}")
    
    if "loginId=" in url_pos_login:
        id_login = url_pos_login.split("loginId=")[1].split("&")[0]
        print(f"\n[SUCESSO] Token de Sessão obtido: {id_login}")
    else:
        print(f"\n[ERRO CRÍTICO] Não conseguiu extrair o loginId da URL.")
        driver.quit()
        input("\nPressione Enter para analisar o erro no ecrã...")
        exit()

    # Fecha o navegador de forma limpa
    driver.quit()
    print("[DEBUG] Navegador fechado com sucesso. Iniciando fase API Requests.")

    # 5. Processamento dos UUIDs via API (Requests + Pandas)
    if not os.path.exists('uuids.csv'):
        print("[ERRO CRÍTICO] O ficheiro 'uuids.csv' não foi encontrado na pasta atual.")
        input("\nPressione Enter para sair...")
        exit()

    print("\n[DEBUG] A abrir o ficheiro 'uuids.csv'...")
    with open('uuids.csv', newline='', encoding='utf-8') as csvfile:
        # Tenta ler com ponto e vírgula
        reader = csv.reader(csvfile, delimiter=';')
        linhas = list(reader)
        print(f"[DEBUG] Total de linhas encontradas no CSV: {len(linhas)}")
        
        for num_linha, row in enumerate(linhas, start=1):
            if not row:
                print(f"[DEBUG] Linha {num_linha} está vazia. Ignorando.")
                continue
            
            if len(row) < 2:
                print(f"[AVISO] Linha {num_linha} não tem colunas suficientes: {row}. A tentar separar por vírgula...")
                # Fallback caso o CSV use vírgulas em vez de ponto e vírgula
                row = row[0].split(',')
                if len(row) < 2:
                    print(f"[ERRO] Linha {num_linha} inválida. Ignorada.")
                    continue

            uuid = row[0].strip()
            quarto = row[1].strip()
            
            url_api = f"http://{site}/webif/gaobjcgi?action=jobCommand&uuid={uuid}&cmd=getLog&loginId={id_login}"
            print(f"\n----------------------------------------")
            print(f"[DEBUG] A processar Linha {num_linha} -> Quarto: {quarto} | UUID: {uuid}")
            print(f"[DEBUG] URL da API: {url_api}")
            
            try:
                print("[DEBUG] A enviar pedido HTTP GET...")
                response = requests.get(url_api, timeout=15)
                print(f"[DEBUG] Resposta da API recebida. Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    print("[DEBUG] A tentar converter resposta para JSON...")
                    json_data = response.json()
                    
                    if 'history' in json_data:
                        total_historico = len(json_data['history'])
                        print(f"[DEBUG] Chave 'history' encontrada no JSON com {total_historico} registos.")
                        
                        if total_historico > 0:
                            print("[DEBUG] A normalizar dados com Pandas DataFrame...")
                            df = pd.json_normalize(json_data['history'])
                            
                            if 'timestamp' in df.columns:
                                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce').dt.tz_localize(None)
                            
                            status_map = {
                                0: 'OK', 1: 'FAULT', 2: 'CONFIRMED', 3: 'OK (prev. fault unconfirmed)'
                            }
                            
                            if 'statusFrom' in df.columns:
                                df['statusFrom'] = df['statusFrom'].map(status_map).fillna(df['statusFrom'])
                            if 'statusTo' in df.columns:
                                df['statusTo'] = df['statusTo'].map(status_map).fillna(df['statusTo'])
                            
                            ficheiro_temporario = 'data.xlsx'
                            df.to_excel(ficheiro_temporario, index=False)
                            print("[DEBUG] DataFrame guardado temporariamente como 'data.xlsx'")
                            
                            nome_ficheiro_final = os.path.join(nome_pasta_logs, f'{quarto}_{data_atual}.xlsx')
                            print(f"[DEBUG] Caminho final do ficheiro: {nome_ficheiro_final}")
                            
                            if os.path.exists(nome_ficheiro_final):
                                os.remove(nome_ficheiro_final)
                                print("[DEBUG] Ficheiro final antigo removido para substituição.")
                                
                            os.rename(ficheiro_temporario, nome_ficheiro_final)
                            
                            print("[DEBUG] A aplicar estilos de cores com Openpyxl...")
                            wb = load_workbook(nome_ficheiro_final)
                            ws = wb.active
                            
                            cores_status = {
                                "OK": "66ff66",
                                "FAULT": "ff6666",
                                "CONFIRMED": "ffff66",
                                "OK (prev. fault unconfirmed)": "6666ff"
