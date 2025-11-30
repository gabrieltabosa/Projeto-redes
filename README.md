# 📡 Projeto de Comunicação Confiável com Criptografia

## 🏷️ Badges  
![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)  
![Criptografia](https://img.shields.io/badge/Criptografia-AES%20256-purple)  
![Protocols](https://img.shields.io/badge/Protocolos-GBN%20%7C%20SR-orange)  
![Status](https://img.shields.io/badge/Status-Ativo-brightgreen)  
![License](https://img.shields.io/badge/License-MIT-lightgrey)  
![OS](https://img.shields.io/badge/Suporte-Windows%20%7C%20Linux%20%7C%20Mac-black)

---

Sistema cliente-servidor que implementa dois protocolos de rede confiáveis (**Go-Back-N** e **Repetição Seletiva**) com criptografia integrada.  
Permite simular diversos tipos de erro em redes e testar a robustez dos protocolos.

⚠️ **Importante:** Para rodar **tanto o servidor quanto o cliente com criptografia**, é **obrigatório** estar com o **ambiente virtual ativado**, pois a biblioteca `cryptography` está instalada apenas nele.

---

## 👥 Integrantes
- Antônio Augusto  
- Pedro Gusmão  
- Felipe Andrade  
- Gabriel Tabosa  
- Guilherme Vinicius  
- Leticia Soares  

---

## 🚀 Como Executar

### **1. Criar e ativar ambiente virtual (recomendado)**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

---

### **2. Instalar dependência no ambiente virtual**

```bash
pip install cryptography
```

---

### **3. Executar o servidor (Terminal 1)**  
*(ambiente virtual deve estar ativado)*

```bash
python server.py
```

---

### **4. Executar o cliente (Terminal 2)**  
*(ambiente virtual deve estar ativado)*

```bash
python client.py
```

---

### **5. Seguir os passos no cliente**

- Escolher modo (**1 = GBN**, **2 = SR**)  
- (Opcional) Simular erros: *timeout, perda, corrupção, duplicação*  
- Definir tamanho da janela (1–5 pacotes)  
- Digitar mensagens para enviar  
- Digitar **"sair"** para encerrar  

---

## ⚙️ Funcionalidades

Handshake de 3 vias • Checksum • Criptografia AES • Retransmissão • Controle de congestionamento
