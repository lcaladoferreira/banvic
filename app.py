import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Função para adicionar rótulos às barras
def add_labels(ax, labels):
    for rect, label in zip(ax.patches, labels):
        height = rect.get_height()
        ax.text(
            rect.get_x() + rect.get_width() / 2, height, label,
            ha='center', va='bottom'
        )

# Configurações do estilo
st.set_page_config(
    page_title="Dashboard BanVic",
    page_icon="💰",  # Exemplo de favicon como emoji de dinheiro
    layout="wide"  # Ajustar layout para modo paisagem
)

# Carregar datasets
agencias = pd.read_csv('agencias.csv')
clientes = pd.read_csv('clientes.csv')
colaborador_agencia = pd.read_csv('colaborador_agencia.csv')
colaboradores = pd.read_csv('colaboradores.csv')
contas = pd.read_csv('contas.csv')
propostas_credito = pd.read_csv('propostas_credito.csv')
transacoes = pd.read_csv('transacoes.csv')

# Mesclar datasets para incluir informações da agência e cliente em transações
transacoes = transacoes.merge(contas[['num_conta', 'cod_agencia', 'cod_cliente']], on='num_conta', how='left')
transacoes = transacoes.merge(agencias[['cod_agencia', 'nome']], on='cod_agencia', how='left')
transacoes.rename(columns={'nome': 'nome_agencia'}, inplace=True)
transacoes = transacoes.merge(clientes[['cod_cliente', 'primeiro_nome', 'ultimo_nome']], on='cod_cliente', how='left')

# Verificar valores nulos
transacoes.fillna({'cod_colaborador': 'Desconhecido'}, inplace=True)
propostas_credito.fillna({'status_proposta': 'Desconhecido'}, inplace=True)

# Validar junções
assert 'cod_agencia' in transacoes.columns, "Junção com DataFrame de Contas falhou"
assert 'nome_agencia' in transacoes.columns, "Junção com DataFrame de Agências falhou"
assert 'primeiro_nome' in transacoes.columns, "Junção com DataFrame de Clientes falhou"

# Pré-processar dados
transacoes['data_transacao'] = pd.to_datetime(transacoes['data_transacao'], errors='coerce').dt.tz_convert(None)
propostas_credito['data_entrada_proposta'] = pd.to_datetime(propostas_credito['data_entrada_proposta'], errors='coerce').dt.tz_convert(None)

dias_semana = {
    'Monday': 'Seg',
    'Tuesday': 'Ter',
    'Wednesday': 'Qua',
    'Thursday': 'Qui',
    'Friday': 'Sex',
    'Saturday': 'Sáb',
    'Sunday': 'Dom'
}
transacoes['dia_da_semana'] = transacoes['data_transacao'].dt.day_name().map(dias_semana)
transacoes['periodo_do_mes'] = transacoes['data_transacao'].dt.day.apply(lambda x: 'início' if x <= 15 else 'fim')

# Filtros interativos
st.sidebar.header("Filtros")

# Definir limites mínimo e máximo de datas com base nos dados
data_minima = transacoes['data_transacao'].min().date()
data_maxima = transacoes['data_transacao'].max().date()

# Filtro por Data
data_inicio = st.sidebar.date_input("Data Início", data_minima, min_value=data_minima, max_value=data_maxima)
data_fim = st.sidebar.date_input("Data Fim", data_maxima, min_value=data_minima, max_value=data_maxima)
transacoes = transacoes[(transacoes['data_transacao'] >= pd.to_datetime(data_inicio)) & (transacoes['data_transacao'] <= pd.to_datetime(data_fim))]

# Filtro por Agência (multiselect)
agencias_list = sorted(transacoes['nome_agencia'].dropna().unique())
agencias_selecionadas = st.sidebar.multiselect("Selecione as Agências", agencias_list, default=agencias_list)

# Filtrar transações pelas agências selecionadas
transacoes_agencia = transacoes[transacoes['nome_agencia'].isin(agencias_selecionadas)]

# Filtro por Cliente (apenas clientes das agências selecionadas)
clientes_agencia = transacoes_agencia[['primeiro_nome', 'ultimo_nome', 'cod_cliente']].dropna().drop_duplicates()
clientes_agencia['nome_completo'] = clientes_agencia['primeiro_nome'].astype(str) + ' ' + clientes_agencia['ultimo_nome'].astype(str)
clientes_list = sorted(clientes_agencia['nome_completo'].unique())
clientes_list.insert(0, 'Todos os Clientes')

# Armazena a seleção atual
clientes_selecionados = st.sidebar.multiselect("Selecione os Clientes", clientes_list, default=['Todos os Clientes'])

# Remover 'Todos os Clientes' se outro cliente for selecionado
if 'Todos os Clientes' in clientes_selecionados and len(clientes_selecionados) > 1:
    clientes_selecionados.remove('Todos os Clientes')

# Filtrar transações pelos clientes selecionados
if 'Todos os Clientes' in clientes_selecionados:
    transacoes_clientes = transacoes_agencia.copy()
else:
    clientes_codigos = clientes_agencia[clientes_agencia['nome_completo'].isin(clientes_selecionados)]['cod_cliente']
    transacoes_clientes = transacoes_agencia[transacoes_agencia['cod_cliente'].isin(clientes_codigos)]

# Aplicar os mesmos filtros à tabela propostas_credito
propostas_filtradas = propostas_credito.copy()

# Filtro por Data em propostas_credito
propostas_filtradas = propostas_filtradas[(propostas_filtradas['data_entrada_proposta'] >= pd.to_datetime(data_inicio)) & (propostas_filtradas['data_entrada_proposta'] <= pd.to_datetime(data_fim))]

# Filtro por Agência em propostas_credito
propostas_filtradas = propostas_filtradas.merge(contas[['cod_cliente', 'cod_agencia']], on='cod_cliente', how='left')
propostas_filtradas = propostas_filtradas[propostas_filtradas['cod_agencia'].isin(agencias[agencias['nome'].isin(agencias_selecionadas)]['cod_agencia'].values)]

# Filtro por Cliente em propostas_credito
if 'Todos os Clientes' not in clientes_selecionados:
    propostas_filtradas = propostas_filtradas[propostas_filtradas['cod_cliente'].isin(transacoes_clientes['cod_cliente'].unique())]

# Calcular KPIs ajustados
# KPI por Data
kpi_data = transacoes_clientes.groupby(transacoes_clientes['data_transacao'].dt.date)['valor_transacao'].agg(['count', 'mean', 'sum']).reset_index()
kpi_data = kpi_data.rename(columns={'data_transacao': 'Data', 'count': 'Contagem', 'mean': 'Média (R$)', 'sum': 'Soma (R$)'})

# KPI por Agência
kpi_agencia = transacoes_clientes.groupby('nome_agencia')['valor_transacao'].agg(['count', 'mean', 'sum']).reset_index()
kpi_agencia = kpi_agencia.rename(columns={'nome_agencia': 'Agência', 'count': 'Contagem', 'mean': 'Média (R$)', 'sum': 'Soma (R$)'})

# KPI por Cliente
kpi_cliente = transacoes_clientes.groupby(['primeiro_nome', 'ultimo_nome'])['valor_transacao'].agg(['count', 'mean', 'sum']).reset_index()
kpi_cliente = kpi_cliente.rename(columns={'primeiro_nome': 'Nome', 'ultimo_nome': 'Sobrenome', 'count': 'Contagem', 'mean': 'Média (R$)', 'sum': 'Soma (R$)'})

# Calcular distribuição de propostas de crédito por status se a coluna existir
if 'status_proposta' in propostas_filtradas.columns:
    propostas_status = propostas_filtradas['status_proposta'].value_counts().reset_index()
    propostas_status.columns = ['Status', 'Contagem']

# Calcular distribuição de transações por cliente
top_n = 10  # Número de principais clientes a serem exibidos
transacoes_cliente = transacoes_clientes.groupby(['primeiro_nome', 'ultimo_nome'])['valor_transacao'].agg(['count', 'sum']).reset_index()
transacoes_cliente = transacoes_cliente.rename(columns={'primeiro_nome': 'Nome', 'ultimo_nome': 'Sobrenome', 'count': 'Contagem', 'sum': 'Soma (R$)'})
transacoes_cliente = transacoes_cliente.round(2)
transacoes_cliente['nome_completo'] = transacoes_cliente['Nome'] + ' ' + transacoes_cliente['Sobrenome']
top_clientes = transacoes_cliente.nlargest(top_n, 'Contagem')

# Arredondar valores para duas casas decimais
kpi_data = kpi_data.round(2)
kpi_agencia = kpi_agencia.round(2)
kpi_cliente = kpi_cliente.round(2)

# Dashboard
st.title('Dashboard BanVic')

# Resposta às perguntas específicas
st.header('Perguntas Específicas')

st.markdown("**Nota:** Nesta seção, são respondidas duas perguntas específicas com base nos dados de transações. Cada coluna dos dataframes exibidos pode ser ordenada ao clicar no cabeçalho da coluna correspondente. Além disso, você pode visualizar os dataframes em tela cheia, procurar por valores específicos e baixar os dados em formato .csv utilizando as opções disponíveis na interface.")

col1, col2 = st.columns(2)

with col1:
    st.subheader('Qual dia da semana apresenta o maior volume médio de transações e qual dia possui o maior valor médio transacionado?')
    st.markdown("**Cálculo:** O volume de transações e o valor médio das transações são calculados para cada dia da semana.")
    trans_vol_dia_cliente = transacoes_clientes.groupby('dia_da_semana')['valor_transacao'].agg(['count', 'mean']).reset_index()
    trans_vol_dia_cliente['dia_da_semana'] = pd.Categorical(trans_vol_dia_cliente['dia_da_semana'], 
                                                            categories=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'], 
                                                            ordered=True)
    trans_vol_dia_cliente = trans_vol_dia_cliente.sort_values('dia_da_semana')
    st.dataframe(trans_vol_dia_cliente.rename(columns={'dia_da_semana': 'Dia da Semana', 'count': 'Contagem', 'mean': 'Média (R$)'}), height=400)

with col2:
    st.subheader('O BanVic observa maiores valores médios de transações no início ou no final do mês?')
    st.markdown("**Cálculo:** O volume de transações e o valor médio das transações são calculados para o início (dias 1-15) e fim (dias 16-31) do mês.")
    trans_vol_mes_cliente = transacoes_clientes.groupby('periodo_do_mes')['valor_transacao'].agg(['count', 'mean']).reset_index()
    trans_vol_mes_cliente['periodo_do_mes'] = pd.Categorical(trans_vol_mes_cliente['periodo_do_mes'],
                                                             categories=['início', 'fim'],
                                                             ordered=True)
    trans_vol_mes_cliente = trans_vol_mes_cliente.sort_values('periodo_do_mes')
    st.dataframe(trans_vol_mes_cliente.rename(columns={'periodo_do_mes': 'Período do Mês', 'count': 'Contagem', 'mean': 'Média (R$)'}), height=400)

# KPI por Data
st.header('KPIs')

st.markdown("Nesta seção, apresentamos os KPIs calculados a partir das transações filtradas.")

col3, col4, col5 = st.columns(3)

with col3:
    st.subheader('KPIs por Data')
    st.markdown("**Cálculo:** Número de transações (Contagem), valor médio das transações (Média) e valor total das transações (Soma) agrupados por data.")
    st.dataframe(kpi_data, height=400)

with col4:
    st.subheader('KPIs por Agência')
    st.markdown("**Cálculo:** Número de transações (Contagem), valor médio das transações (Média) e valor total das transações (Soma) agrupados por agência.")
    st.dataframe(kpi_agencia, height=400)

with col5:
    st.subheader('KPIs por Cliente')
    st.markdown("**Cálculo:** Número de transações (Contagem), valor médio das transações (Média) e valor total das transações (Soma) agrupados por cliente.")
    st.dataframe(kpi_cliente, height=400)

# Visualizações para os Clientes
st.subheader(f"Média por Período do Mês de: {', '.join(clientes_selecionados)}")
fig_mes_cliente, (ax3, ax4) = plt.subplots(1, 2, figsize=(18, 8))

# Volume de transações por período do mês (Clientes)
sns.barplot(data=trans_vol_mes_cliente, x='periodo_do_mes', y='count', ax=ax3, palette='muted')
ax3.set_title('Volume Médio de Transações por Período do Mês (Clientes)')
ax3.set_ylabel('')
ax3.set_xlabel('')
ax3.yaxis.set_visible(False)
add_labels(ax3, trans_vol_mes_cliente['count'].round(0).astype(int).astype(str))

# Valor médio de transações por período do mês (Clientes)
sns.barplot(data=trans_vol_mes_cliente, x='periodo_do_mes', y='mean', ax=ax4, palette='muted')
ax4.set_title('Valor Médio de Transações por Período do Mês (R$) (Clientes)')
ax4.set_ylabel('')
ax4.set_xlabel('')
ax4.yaxis.set_visible(False)
add_labels(ax4, trans_vol_mes_cliente['mean'].round(2).astype(str))

st.pyplot(fig_mes_cliente)

# Distribuição de propostas de crédito por status
if 'propostas_status' in locals():
    fig_propostas, ax_propostas = plt.subplots(figsize=(10, 6))
    sns.barplot(data=propostas_status, x='Status', y='Contagem', ax=ax_propostas, palette='muted')
    ax_propostas.set_title('Distribuição de Propostas de Crédito por Status')
    ax_propostas.set_ylabel('')
    ax_propostas.set_xlabel('')
    ax_propostas.yaxis.set_visible(False)
    add_labels(ax_propostas, propostas_status['Contagem'].astype(str))

    st.pyplot(fig_propostas)

# Visualizações para a Agência
st.subheader(f"Média por Período do Mês de: {', '.join(agencias_selecionadas)}")
fig_mes_agencia, (ax7, ax8) = plt.subplots(1, 2, figsize=(18, 8))

# Volume de transações por período do mês (Agência)
trans_vol_mes_agencia = transacoes_clientes.groupby(['nome_agencia', 'periodo_do_mes'])['valor_transacao'].agg(['count', 'mean']).reset_index()
trans_vol_mes_agencia = trans_vol_mes_agencia[trans_vol_mes_agencia['nome_agencia'].isin(agencias_selecionadas)]
trans_vol_mes_agencia['periodo_do_mes'] = pd.Categorical(trans_vol_mes_agencia['periodo_do_mes'],
                                                         categories=['início', 'fim'],
                                                         ordered=True)
trans_vol_mes_agencia = trans_vol_mes_agencia.sort_values('periodo_do_mes')

sns.barplot(data=trans_vol_mes_agencia, x='periodo_do_mes', y='count', ax=ax7, palette='muted')
ax7.set_title('Volume Médio de Transações por Período do Mês (Agência)')
ax7.set_ylabel('')
ax7.set_xlabel('')
ax7.yaxis.set_visible(False)
add_labels(ax7, trans_vol_mes_agencia['count'].round(0).astype(int).astype(str))

# Valor médio de transações por período do mês (Agência)
sns.barplot(data=trans_vol_mes_agencia, x='periodo_do_mes', y='mean', ax=ax8, palette='muted')
ax8.set_title('Valor Médio de Transações por Período do Mês (R$) (Agência)')
ax8.set_ylabel('')
ax8.set_xlabel('')
ax8.yaxis.set_visible(False)
add_labels(ax8, trans_vol_mes_agencia['mean'].round(2).astype(str))

st.pyplot(fig_mes_agencia)

# Distribuição de transações por cliente
if not top_clientes.empty:
    fig_cliente, (ax_cl1, ax_cl2) = plt.subplots(1, 2, figsize=(18, 8))
    
    # Ordenar os dados do maior para o menor
    top_clientes = top_clientes.sort_values('Contagem', ascending=False)
    
    sns.barplot(data=top_clientes, x='nome_completo', y='Contagem', ax=ax_cl1, palette='muted')
    ax_cl1.set_title('Clientes com o Maior Volume Médio de Transações')
    ax_cl1.set_ylabel('')
    ax_cl1.set_xlabel('')
    ax_cl1.yaxis.set_visible(False)
    ax_cl1.set_xticklabels(ax_cl1.get_xticklabels(), rotation=45, ha='right')
    add_labels(ax_cl1, top_clientes['Contagem'].astype(str))

    # Ordenar os dados do maior para o menor
    top_clientes = top_clientes.sort_values('Soma (R$)', ascending=False)
    
    sns.barplot(data=top_clientes, x='nome_completo', y='Soma (R$)', ax=ax_cl2, palette='muted')
    ax_cl2.set_title('Clientes com Maior Valor Médio Total de Transações (R$)')
    ax_cl2.set_ylabel('')
    ax_cl2.set_xlabel('')
    ax_cl2.yaxis.set_visible(False)
    ax_cl2.set_xticklabels(ax_cl2.get_xticklabels(), rotation=45, ha='right')
    add_labels(ax_cl2, top_clientes['Soma (R$)'].astype(str))

    st.pyplot(fig_cliente)
