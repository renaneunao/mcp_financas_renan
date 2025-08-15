from flask import Blueprint, render_template, request
from app.database import get_db_connection
from app.routes.auth import login_required, get_current_user_id
from datetime import datetime, date
import calendar

dashboard_bp = Blueprint('dashboard', __name__)

def calcular_saldo_mes_dinamico(ano, mes, user_id):
    """Calcula o saldo acumulado até o final de um mês específico para um usuário"""
    from datetime import date
    import calendar
    
    conn = get_db_connection()
    
    # Calcular o último dia do mês
    ultimo_dia = date(ano, mes, calendar.monthrange(ano, mes)[1])
    
    # Somar todas as receitas até o final do mês para o usuário
    receitas = conn.execute('''
        SELECT COALESCE(SUM(valor), 0) as total
        FROM receita 
        WHERE data_inicio <= ? AND usuario_id = ?
    ''', (ultimo_dia, user_id)).fetchone()
    
    # Somar todas as despesas até o final do mês para o usuário
    despesas = conn.execute('''
        SELECT COALESCE(SUM(valor), 0) as total
        FROM despesa 
        WHERE data_inicio <= ? AND usuario_id = ?
    ''', (ultimo_dia, user_id)).fetchone()
    
    conn.close()
    
    saldo = receitas['total'] - despesas['total']
    return saldo

@dashboard_bp.route('/')
@login_required
def index():
    # Obter ID do usuário logado
    user_id = get_current_user_id()
    
    # Obter mês e ano atual ou do parâmetro
    now = datetime.now()
    mes = int(request.args.get('mes', now.month))
    ano = int(request.args.get('ano', now.year))
    
    # Validar mês e ano
    if mes < 1 or mes > 12:
        mes = now.month
    if ano < 2000 or ano > 2100:
        ano = now.year

    # Calcular saldo do mês anterior
    mes_anterior = mes - 1 if mes > 1 else 12
    ano_anterior = ano if mes > 1 else ano - 1
    
    saldo_anterior = calcular_saldo_mes_dinamico(ano_anterior, mes_anterior, user_id)
    
    # Conectar ao banco
    conn = get_db_connection()
    
    # Calcular primeiro e último dia do mês
    primeiro_dia = date(ano, mes, 1)
    ultimo_dia = date(ano, mes, calendar.monthrange(ano, mes)[1])
    
    # Buscar receitas do mês para o usuário
    receitas = conn.execute('''
        SELECT r.*, cr.nome as categoria_nome, 
               COALESCE(sr.nome, 'Sem subcategoria') as subcategoria_nome
        FROM receita r
        JOIN categoria_receita cr ON r.categoria_id = cr.id
        LEFT JOIN subcategoria_receita sr ON r.subcategoria_id = sr.id
        WHERE r.data_inicio BETWEEN ? AND ? AND r.usuario_id = ?
        ORDER BY r.data_inicio DESC
    ''', (primeiro_dia, ultimo_dia, user_id)).fetchall()
    
    # Converter para lista para poder adicionar o saldo anterior
    receitas = list(receitas)
    
    # Adicionar saldo anterior como receita virtual se positivo
    if saldo_anterior > 0:
        receita_virtual = type('obj', (object,), {
            'id': None,
            'categoria_nome': 'Saldo Anterior',
            'subcategoria_nome': f'{mes_anterior:02d}/{ano_anterior}',
            'data_inicio': primeiro_dia.isoformat(),
            'valor': saldo_anterior,
            'tipo_recorrencia': 'unica',
            'numero_parcelas': '1',
            'parcela_atual': 1,
            'virtual': True
        })()
        receitas.insert(0, receita_virtual)
    
    # Buscar despesas do mês para o usuário
    despesas = conn.execute('''
        SELECT d.*, cd.nome as categoria_nome, 
               COALESCE(sd.nome, 'Sem subcategoria') as subcategoria_nome
        FROM despesa d
        JOIN categoria_despesa cd ON d.categoria_id = cd.id
        LEFT JOIN subcategoria_despesa sd ON d.subcategoria_id = sd.id
        WHERE d.data_inicio BETWEEN ? AND ? AND d.usuario_id = ?
        ORDER BY d.data_inicio DESC
    ''', (primeiro_dia, ultimo_dia, user_id)).fetchall()
    
    # Converter para lista para poder adicionar o déficit anterior
    despesas = list(despesas)
    
    # Adicionar déficit anterior como despesa virtual se negativo
    if saldo_anterior < 0:
        despesa_virtual = type('obj', (object,), {
            'id': None,
            'categoria_nome': 'Déficit Anterior',
            'subcategoria_nome': f'{mes_anterior:02d}/{ano_anterior}',
            'data_inicio': primeiro_dia.isoformat(),
            'valor': abs(saldo_anterior),
            'tipo_recorrencia': 'unica',
            'numero_parcelas': '1',
            'parcela_atual': 1,
            'virtual': True
        })()
        despesas.insert(0, despesa_virtual)

    # Calcular totais (incluindo saldo anterior se existir)
    total_receitas = sum(float(r.valor if hasattr(r, 'valor') else r['valor']) for r in receitas)
    total_despesas = sum(float(d.valor if hasattr(d, 'valor') else d['valor']) for d in despesas)
    saldo = total_receitas - total_despesas
    
    # Buscar totais por categoria de receita para o usuário (excluindo virtuais)
    receitas_por_categoria = conn.execute('''
        SELECT cr.nome, SUM(r.valor) as total
        FROM receita r
        JOIN categoria_receita cr ON r.categoria_id = cr.id
        WHERE r.data_inicio BETWEEN ? AND ? AND r.usuario_id = ?
        GROUP BY cr.id, cr.nome
        ORDER BY total DESC
    ''', (primeiro_dia, ultimo_dia, user_id)).fetchall()
    
    # Buscar totais por categoria de despesa para o usuário
    despesas_por_categoria = conn.execute('''
        SELECT cd.nome, SUM(d.valor) as total
        FROM despesa d
        JOIN categoria_despesa cd ON d.categoria_id = cd.id
        WHERE d.data_inicio BETWEEN ? AND ? AND d.usuario_id = ?
        GROUP BY cd.id, cd.nome
        ORDER BY total DESC
    ''', (primeiro_dia, ultimo_dia, user_id)).fetchall()
    
    conn.close()
    
    # Gerar lista de meses para navegação
    meses_nomes = [
        '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    
    meses = [
        {'numero': i, 'nome': meses_nomes[i]}
        for i in range(1, 13)
    ]
    
    return render_template('dashboard/index.html',
                         receitas=receitas,
                         despesas=despesas,
                         total_receitas=total_receitas,
                         total_despesas=total_despesas,
                         saldo=saldo,
                         saldo_anterior=saldo_anterior,
                         mes_anterior=mes_anterior,
                         ano_anterior=ano_anterior,
                         receitas_por_categoria=receitas_por_categoria,
                         despesas_por_categoria=despesas_por_categoria,
                         mes_atual=mes,
                         ano_atual=ano,
                         nome_mes=meses_nomes[mes],
                         meses=meses)
