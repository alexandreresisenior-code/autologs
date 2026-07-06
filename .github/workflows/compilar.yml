name: Gerar Executavel Windows

on:
  workflow_dispatch: # Permite que você clique em um botão para gerar o arquivo quando quiser

jobs:
  build:
    runs-on: windows-latest

    steps:
    - name: Baixando o codigo
      uses: actions/checkout@v4

    - name: Configurando o Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Instalar dependencias
      run: |
        pip install selenium pyinstaller

    - name: Criar o arquivo .EXE
      run: |
        pyinstaller --onefile auto_logs.py

    - name: Disponibilizar para Download
      uses: actions/upload-artifact@v4
      with:
        name: Executavel-Windows
        path: dist/auto_logs.exe
