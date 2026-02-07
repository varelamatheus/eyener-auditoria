import streamlit as st
import requests
import base64
import json
import re
import urllib.parse
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Eyener | Eficiência com Visão de Dono",
    page_icon="⚡",
    layout="centered"
)

# --- CONFIGURAÇÕES ---
# Tenta pegar dos Segredos (Nuvem) OU usa a variável local (PC) se não achar
# Isso garante que funcione tanto no seu PC quanto na Web sem mudar código
MINHA_CHAVE = st.secrets.get("GEMINI_KEY", "SUA_CHAVE_AQUI")
SEU_WHATSAPP = st.secrets.get("ZAP_NUMBER", "555499999999") 
NOME_MODELO = "gemini-flash-latest"


# --- FUNÇÕES ---
def extrair_json_do_texto(texto_sujo):
    try:
        padrao = r"\{[\s\S]*\}"
        match = re.search(padrao, texto_sujo)
        if match: return match.group(0)
        else: return texto_sujo
    except: return texto_sujo

@st.cache_data(show_spinner=False) 
def analisar_fatura_api(arquivo_bytes):
    try:
        pdf_base64 = base64.b64encode(arquivo_bytes).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{NOME_MODELO}:generateContent?key={MINHA_CHAVE}"
        headers = {'Content-Type': 'application/json'}
        
        # --- PROMPT REFINADO (MODO XERIFE) ---
        prompt = """
        Atue como auditor sênior da Eyener. Analise a fatura de energia (Grupo A).
        
        REGRAS ESTRITAS PARA EXTRAÇÃO FINANCEIRA (R$):
        
        1. Demanda Contratada e Medida: Extraia os valores em kW.
        
        2. "Diferença de Demanda" ou "Demanda Complementar":
           - Procure o valor R$ total cobrado por este item específico.
        
        3. "Ultrapassagem":
           - Procure o valor R$ total da multa de demanda excedente.
        
        4. "Energia Reativa" ou "Reativo Excedente":
           - ATENÇÃO: Só retorne o valor se for uma MULTA/COBRANÇA EXCEDENTE explícita maior que R$ 10,00. 
           - Ignore pequenos valores de impostos (PIS/COFINS) sobre o reativo. Se não houver multa clara, retorne 0.0.
        
        Se não encontrar um valor, retorne 0.0.
        
        SAÍDA JSON OBRIGATÓRIA:
        {
            "nome_cliente": "texto",
            "demanda_contratada_kw": numero,
            "demanda_medida_kw": numero,
            "valor_diferenca_demanda_reais": numero,
            "valor_multa_ultrapassagem_reais": numero,
            "valor_multa_reativo_reais": numero
        }
        """
        data = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "application/pdf", "data": pdf_base64}}]}]}
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            txt = response.json()['candidates'][0]['content']['parts'][0]['text']
            return json.loads(extrair_json_do_texto(txt))
        return None
    except: return None

# --- DESIGN DA PÁGINA ---

col_logo, col_titulo = st.columns([2, 3]) # Ajustei a proporção para a logo maior
with col_logo:
    if os.path.exists("logo.png"):
        # AQUI: Aumentei para 400px
        st.image("logo.png", width=400) 
    else:
        st.write("# ⚡")

with col_titulo:
    st.markdown("<div style='padding-top: 40px;'>", unsafe_allow_html=True) # Mais espaço no topo
    st.markdown("<h1 style='color: white; margin-bottom: 0px;'>Eyener - Eficiência com Visão de Dono</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #E0E0E0;'>Auditoria de Faturas de Energia de Indústrias (Grupo A)</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

st.markdown("### 📂 Envie aqui sua fatura")
st.markdown("<p style='color: #CCCCCC; font-size: 0.9em;'>Arraste o PDF da sua conta de luz aqui para uma análise instantânea.</p>", unsafe_allow_html=True)

st.markdown("""
<style>
    [data-testid='stFileUploader'] {
        background-color: #193D5A;
        border: 2px dashed #4A6FA5;
        padding: 30px;
        border-radius: 15px;
    }
    [data-testid='stFileUploader']:hover {
        border-color: #FFFFFF;
    }
</style>
""", unsafe_allow_html=True)

arquivo = st.file_uploader("Upload do PDF", type=["pdf"], label_visibility="collapsed")

# --- Aviso de Privacidade (LGPD) ---
st.markdown(
    """
    <div style='background-color: rgba(37, 211, 102, 0.1); border: 1px solid #25D366; padding: 10px; border-radius: 8px; text-align: center; margin-top: 10px;'>
        🔒 <strong>Privacidade Garantida:</strong> Seus dados são processados apenas para esta análise e não são armazenados. 
        <br><span style='font-size: 0.85em;'>Estamos em total conformidade com a <strong>LGPD</strong> (Lei Geral de Proteção de Dados).</span>
    </div>
    """, 
    unsafe_allow_html=True
)

if arquivo:
    with st.spinner("🔍 A IA da Eyener está processando os dados..."):
        dados = analisar_fatura_api(arquivo.getvalue())
    
    if dados:
        contratada = float(dados.get('demanda_contratada_kw') or 0)
        medida = float(dados.get('demanda_medida_kw') or 0)
        v_desp = float(dados.get('valor_diferenca_demanda_reais') or 0)
        v_ultra = float(dados.get('valor_multa_ultrapassagem_reais') or 0)
        v_reat = float(dados.get('valor_multa_reativo_reais') or 0)
        
        # --- REDE DE SEGURANÇA MATEMÁTICA (Reforçada) ---
        # Se a IA não achou valor explícito de desperdício, mas a matemática mostra uma sobra grande (>10%)
        margem_seguranca = contratada * 0.10
        sobra_matematica = contratada - medida
        
        # Se a sobra for maior que a margem e o valor lido for zero (ou muito baixo, erro da IA)
        if sobra_matematica > margem_seguranca and v_desp < 10.0:
             # Força o cálculo estimado
             v_desp = sobra_matematica * 35.00 # Tarifa estimada R$ 35/kW

        total_perda = v_desp + v_ultra + v_reat
        anual_perda = total_perda * 12
        cliente = dados.get('nome_cliente', 'Sua Empresa')

        st.markdown("---")
        st.markdown(f"### 📊 Diagnóstico: {cliente}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Contratada", f"{contratada} kW")
        c2.metric("Medida", f"{medida} kW")
        
        if total_perda > 0:
            c3.metric("Desperdício Detectado", f"R$ {total_perda:,.2f}", delta="- Ação Necessária", delta_color="inverse")
            
            with st.container(border=True):
                st.error(f"🚨 **ALERTA CRÍTICO:** Desperdício de **R$ {total_perda:,.2f}** nesta fatura.")
                st.markdown(f"#### Projeção de prejuízo anual: :orange[**R$ {anual_perda:,.2f}**]")
                st.divider()
                st.markdown("**Onde está o vazamento:**")
                if v_desp > 0: st.caption(f"📉 Contrato Ocioso: R$ {v_desp:,.2f}")
                if v_ultra > 0: st.caption(f"⚠️ Multa Ultrapassagem: R$ {v_ultra:,.2f}")
                if v_reat > 0: st.caption(f"⚡ Multa Reativo: R$ {v_reat:,.2f}")

            st.markdown("---")
            st.markdown("### 💡 Solução Eyener")
            st.write("Nossa engenharia pode eliminar esse custo. Envie uma mensagem agora para receber a solução.")
            
            with st.form("form_whatsapp"):
                col_in1, col_in2 = st.columns(2)
                with col_in1: nome_lead = st.text_input("Seu Nome")
                with col_in2: empresa_lead = st.text_input("Nome da Empresa", value=cliente)
                
                st.info("ℹ️ Ao clicar abaixo, o WhatsApp Web abrirá. **Lembre-se de anexar este PDF** na conversa.")
                anexar_check = st.checkbox("Entendi, vou enviar o PDF no WhatsApp.")
                
                gerar_link = st.form_submit_button("📞 RECEBER SOLUÇÃO TÉCNICA", type="primary", use_container_width=True)

            if gerar_link:
                if not nome_lead: st.warning("⚠️ Preencha seu nome.")
                elif not anexar_check: st.warning("⚠️ Confirme que enviará o PDF.")
                else:
                    mensagem_zap = f"Olá Eyener! Sou *{nome_lead}*, da *{empresa_lead}*.\n\nO auditor automático de faturas da Eyener identificou um desperdício de *R$ {total_perda:,.2f}* na minha fatura.\n\n*Estou enviando o PDF da fatura em anexo agora* para análise."
                    mensagem_encoded = urllib.parse.quote(mensagem_zap)
                    link_zap = f"https://wa.me/{SEU_WHATSAPP}?text={mensagem_encoded}"
                    
                    st.success("Link gerado! Clique abaixo:")
                    st.markdown(f"""<a href="{link_zap}" target="_blank" style="text-decoration:none;"><div style="background-color: #25D366; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 18px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">📲 ABRIR WHATSAPP E ENVIAR PDF</div></a>""", unsafe_allow_html=True)
            
        else:
            st.success("✅ **Eficiência Máxima!** Fatura otimizada, sem multas ou desperdícios.")
            st.balloons()