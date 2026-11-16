import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).with_name("desperdicio_zero.db")

# Etapas transcritas do fluxograma enviado.
ETAPAS_INICIAIS = [
    ("Coleta de Dados", "Etapa inicial", 7),
    ("Analisar Fornecedores", "Fornecedores e aquisição", 2),
    ("Consulta Nutricional e Estudo de Safras", "Fornecedores e aquisição", 5),
    ("Montagem de Catálogo e Cronograma de Aquisições Alimentares", "Fornecedores e aquisição", 2),
    ("Consulta de Satisfação", "Preferências alimentares", 5),
    ("Entender o Cardápio Mais Elogiado", "Preferências alimentares", 1),
    ("Montagem do Cardápio Visando Redução de Desperdício", "Planejamento do cardápio", 2),
    ("Analisar Custos e Logística", "Custos e logística", 5),
    ("Analisar Riscos da Operação e Rentabilidade", "Custos e logística", 5),
    ("Redução de Custos e Ampliação de Bocas Alimentadas", "Custos e logística", 5),
    ("Distribuição Alimentar em Áreas com Maior Insegurança Alimentar de Fortaleza", "Distribuição", 3),
]

def conectar():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def preparar_banco():
    with conectar() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS etapas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                frente TEXT NOT NULL,
                duracao INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pendente',
                observacoes TEXT DEFAULT ''
            )
        """)
        total = conn.execute("SELECT COUNT(*) FROM etapas").fetchone()[0]
        if total == 0:
            conn.executemany(
                "INSERT INTO etapas (nome, frente, duracao) VALUES (?, ?, ?)",
                ETAPAS_INICIAIS
            )

def carregar_etapas():
    with conectar() as conn:
        return pd.read_sql_query(
            "SELECT id, nome, frente, duracao, status, observacoes FROM etapas ORDER BY id",
            conn
        )

def salvar_etapa(etapa_id, status, observacoes):
    with conectar() as conn:
        conn.execute(
            "UPDATE etapas SET status = ?, observacoes = ? WHERE id = ?",
            (status, observacoes, etapa_id)
        )

st.set_page_config(page_title="Desperdício Zero", page_icon="🌱", layout="wide")
preparar_banco()

st.title("🌱 Desperdício Zero")
st.caption("Sistema de acompanhamento do projeto de redução do desperdício alimentar e distribuição de alimentos em Fortaleza.")

df = carregar_etapas()
total = len(df)
concluidas = int((df["status"] == "Concluída").sum())
andamento = int((df["status"] == "Em andamento").sum())
pendentes = int((df["status"] == "Pendente").sum())
progresso = concluidas / total if total else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de etapas", total)
c2.metric("Concluídas", concluidas)
c3.metric("Em andamento", andamento)
c4.metric("Pendentes", pendentes)

st.subheader("Progresso geral")
st.progress(progresso, text=f"{progresso:.0%} das etapas concluídas")

aba_painel, aba_etapas, aba_relatorio = st.tabs(["Visão geral", "Gerenciar etapas", "Relatório"])

with aba_painel:
    st.subheader("Etapas por frente de trabalho")
    resumo = df.groupby(["frente", "status"]).size().unstack(fill_value=0)
    st.bar_chart(resumo)
    st.subheader("Cronograma previsto")
    visao = df[["nome", "frente", "duracao", "status"]].copy()
    visao.columns = ["Atividade", "Frente de trabalho", "Duração (dias)", "Situação"]
    st.dataframe(visao, use_container_width=True, hide_index=True)
    st.info("As frentes de trabalho podem ocorrer em paralelo, conforme as ligações do fluxograma original. A duração de cada atividade é a estimativa indicada no documento.")

with aba_etapas:
    st.subheader("Atualizar situação das atividades")
    st.write("Selecione uma atividade para atualizar seu andamento e registrar observações.")
    opcoes = {f'{row["id"]} — {row["nome"]}': int(row["id"]) for _, row in df.iterrows()}
    selecionada = st.selectbox("Atividade", list(opcoes.keys()))
    etapa_id = opcoes[selecionada]
    atual = df[df["id"] == etapa_id].iloc[0]
    with st.form("form_etapa"):
        novo_status = st.selectbox(
            "Situação",
            ["Pendente", "Em andamento", "Concluída"],
            index=["Pendente", "Em andamento", "Concluída"].index(atual["status"])
        )
        novas_observacoes = st.text_area("Observações", value=atual["observacoes"] or "")
        salvar = st.form_submit_button("Salvar atualização", type="primary")
        if salvar:
            salvar_etapa(etapa_id, novo_status, novas_observacoes)
            st.success("Etapa atualizada com sucesso.")
            st.rerun()

with aba_relatorio:
    st.subheader("Resumo do projeto")
    st.write(f"O projeto possui **{total} atividades** cadastradas.")
    st.write(f"- **{concluidas}** concluídas")
    st.write(f"- **{andamento}** em andamento")
    st.write(f"- **{pendentes}** pendentes")
    st.write(f"- **{progresso:.0%}** de conclusão geral")
    st.download_button(
        "Baixar relatório em CSV",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="relatorio_desperdicio_zero.csv",
        mime="text/csv"
    )

st.divider()
st.caption("Protótipo acadêmico — os dados são armazenados localmente em um banco SQLite.")
