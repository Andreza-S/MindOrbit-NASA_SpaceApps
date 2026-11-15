# Publicar o MindOrbit / Deploying MindOrbit

Recomendado: **Streamlit Community Cloud** (gratuito, link público, atualiza sozinho quando você envia mudanças ao GitHub).

## Como funciona na hospedagem
- Com `MINDORBIT_PER_SESSION=1`, **cada visitante recebe o seu próprio banco**, que começa no dia 1. Ninguém mexe na demo de outra pessoa.
- Atualizar a página do navegador começa uma sessão nova, ou seja, volta ao dia 1.
- Os bancos ficam em arquivos temporários e os de mais de 12 h são apagados. O disco da hospedagem é temporário; nada precisa ser guardado.
- O app abre em inglês (seletor "Language" no topo).

## Passo a passo

### 1. Conta e repositório no GitHub
1. Crie uma conta em https://github.com (se ainda não tiver).
2. Clique em **New repository**. Nome: `mindorbit`. Marque **Public** (mais simples; o repositório não tem segredos) e clique em **Create repository**.

### 2. Enviar o projeto
A raiz do repositório precisa ter o `app.py` (o conteúdo da pasta `mindorbit`, não a pasta de fora).

**Com Git (PowerShell, dentro da pasta `mindorbit`):**
```powershell
git init
git add .
git commit -m "MindOrbit"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/mindorbit.git
git push -u origin main
```
(O `.gitignore` já deixa de fora o banco local, a chave do link e o `.venv`.)

**Sem Git:** na página do repositório, **Add file → Upload files**, arraste o conteúdo da pasta (as subpastas incluídas; o GitHub aceita até 100 arquivos por envio, então envie em duas levas se precisar) e clique em **Commit changes**. Não envie `.venv`, `__pycache__`, `data/mindorbit.db` nem `data/link.key`.

### 3. Publicar no Streamlit Community Cloud
1. Acesse https://share.streamlit.io e entre com a conta do GitHub.
2. **Create app → Deploy a public app from GitHub**.
3. Repository: `SEU_USUARIO/mindorbit` · Branch: `main` · Main file path: `app.py`.
4. Abra **Advanced settings**:
   - **Python version:** 3.11
   - **Secrets** (cole exatamente):
     ```toml
     MINDORBIT_PER_SESSION = "1"
     ```
5. Clique em **Deploy**. A primeira subida leva alguns minutos (instala os pacotes). Ao terminar você recebe o link `https://....streamlit.app`.

### 4. Conferir
- Abra o link em uma janela anônima e em outro navegador ao mesmo tempo: cada um deve estar no **dia 1**, e avançar o dia em um não pode mudar o outro.
- Troque o idioma (Language), escreva um diário em português, avance alguns dias, abra a aba Terra.
- Se o app ficar parado por dias, a plataforma o "dorme"; o primeiro acesso depois acorda em alguns segundos.

### Se algo falhar
- **Erro de módulo:** confira se o `requirements.txt` está na raiz do repositório.
- **Tela de erro ao abrir:** em **Manage app → Logs** aparece a mensagem; me mande que eu resolvo.
- **Quer outra hospedagem:** funciona igual em Hugging Face Spaces (tipo Streamlit) ou em qualquer servidor com `pip install -r requirements.txt` e `streamlit run app.py`, com `MINDORBIT_PER_SESSION=1` definido.

---

## English summary
Host on Streamlit Community Cloud: push this folder to a GitHub repo (root must contain `app.py`), then at share.streamlit.io create an app from that repo, set Python 3.11 and add the secret `MINDORBIT_PER_SESSION = "1"`. With it, every visitor gets a private temporary database that starts at mission day 1; reloading the page restarts the demo. The app opens in English (language selector at the top).
