# 4. Realiza o Login (Adaptado para CODESYS / WebVisu)
    print(f"Acessando página de login: {url_login}")
    driver.get(url_login)
    
    # Passo A: Clicar no botão inicial de login (Manual Login)
    print("Aguardando o botão de Login aparecer na tela...")
    # Tenta encontrar por texto. Se o seu botão disser "Manual Login", altere abaixo para "Manual Login"
    try:
        botao_login_inicial = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Login') or contains(text(), 'Manual')]")))
        botao_login_inicial.click()
        print("Botão inicial clicado. Aguardando campos de texto...")
        time.sleep(2) # Pausa para a animação do form abrir
    except Exception:
        print("Aviso: Não encontrou o botão por texto, tentando prosseguir assumindo que o form já possa estar aberto...")

    # Passo B: Preencher Usuário e Senha
    # Como no WebVisu inputs às vezes não têm ID fixo, buscamos pelo tipo do elemento ou ordem na página
    print("Preenchendo dados de acesso...")
    
    # Localiza o campo de usuário (geralmente o primeiro input de texto ou o elemento logo após o texto 'User name')
    try:
        campo_usuario = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text']")))
    except Exception:
        # Alternativa caso o WebVisu use campos customizados: procura pelo campo perto do texto "User"
        campo_usuario = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'User')]/following::input[1]")))
        
    campo_usuario.clear()
    campo_usuario.send_keys(usuario)

    # Localiza o campo de senha (geralmente o input do tipo 'password' ou o segundo input da tela)
    try:
        campo_senha = driver.find_element(By.XPATH, "//input[@type='password']")
    except Exception:
        campo_senha = driver.find_element(By.XPATH, "//*[contains(text(), 'Password')]/following::input[1]")
        
    campo_senha.clear()
    campo_senha.send_keys(senha)

    # Passo C: Clicar no botão 'OK' ou 'Entrar' do formulário
    print("Confirmando o login...")
    try:
        # Procura um botão que diz 'OK', 'Log-In' ou o botão de submit do form
        botao_confirmar = driver.find_element(By.XPATH, "//*[text()='OK' or text()='Ok' or text()='Log-In' or @type='submit']")
        botao_confirmar.click()
    except Exception:
        # Se falhar, tenta simular o "Enter" no teclado dentro do campo de senha
        from selenium.webdriver.common.keys import Keys
        campo_senha.send_keys(Keys.ENTER)

    # Aguarda o painel carregar após o login
    time.sleep(5) 
    print("Login efetuado com sucesso!")
