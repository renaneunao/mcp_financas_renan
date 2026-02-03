from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.database import get_db_connection, get_categorias_despesas, get_subcategorias_despesas, gerar_parcelas_despesa, get_cartoes_credito
from app.routes.auth import login_required, get_current_user_id
from datetime import datetime
from dateutil.relativedelta import relativedelta

despesas_bp = Blueprint('despesas', __name__, url_prefix='/despesas')

@despesas_bp.route('/toggle-pagamento/<int:id>', methods=['POST'])
@login_required
def toggle_pagamento(id):
    """Alterna o status de pagamento de uma despesa"""
    user_id = get_current_user_id()
    conn = get_db_connection()
    
    try:
        # Verificar se a despesa pertence ao usuário
        despesa = conn.execute(
            'SELECT pago FROM despesa WHERE id = ? AND usuario_id = ?', 
            (id, user_id)
        ).fetchone()
        
        if not despesa:
            return jsonify({'success': False, 'message': 'Despesa não encontrada'}), 404
        
        # Alternar status
        novo_status = not despesa['pago']
        
        # Verificar opção de pagar fatura inteira
        pagar_fatura = request.json.get('pagar_fatura') if request.json else False
        
        if pagar_fatura:
            # Buscar info para atualizar tudo da mesma instituição e mês
            dados_cartao = conn.execute('''
                SELECT c.instituicao_id, d.data_inicio
                FROM despesa d
                JOIN cartao_credito c ON d.cartao_id = c.id
                WHERE d.id = ?
            ''', (id,)).fetchone()
            
            if dados_cartao:
                vencimento = datetime.strptime(dados_cartao['data_inicio'], '%Y-%m-%d')
                
                rows = conn.execute('''
                    UPDATE despesa 
                    SET pago = ?
                    WHERE id IN (
                        SELECT d2.id 
                        FROM despesa d2
                        JOIN cartao_credito c2 ON d2.cartao_id = c2.id
                        WHERE d2.usuario_id = ?
                        AND c2.instituicao_id = ?
                        AND strftime('%m', d2.data_inicio) = ? 
                        AND strftime('%Y', d2.data_inicio) = ?
                        AND d2.pago = ?
                    )
                ''', (
                    novo_status,
                    user_id, 
                    dados_cartao['instituicao_id'], 
                    f'{vencimento.month:02d}', 
                    str(vencimento.year),
                    not novo_status
                ))
                
                msg = f'Fatura {"paga" if novo_status else "reaberta"} com sucesso! ({rows.rowcount} itens atualizados)'
                
                # Commit para confirmar pagamento em massa
                conn.commit()
                conn.close()
                return jsonify({
                    'success': True, 
                    'pago': novo_status,
                    'message': msg
                })

        # Pagamento normal individual
        conn.execute(
            'UPDATE despesa SET pago = ? WHERE id = ? AND usuario_id = ?',
            (novo_status, id, user_id)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'pago': novo_status,
            'message': 'Pagamento confirmado' if novo_status else 'Pagamento desmarcado'
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@despesas_bp.route('/check-fatura/<int:id>')
@login_required
def check_fatura(id):
    """Verifica se há outras despesas da mesma fatura pendentes"""
    user_id = get_current_user_id()
    conn = get_db_connection()
    
    try:
        # Buscar dados da despesa e do cartão
        despesa = conn.execute('''
            SELECT d.*, c.instituicao_id, c.nome_cartao, i.nome as instituicao_nome 
            FROM despesa d
            LEFT JOIN cartao_credito c ON d.cartao_id = c.id
            LEFT JOIN instituicao_financeira i ON c.instituicao_id = i.id
            WHERE d.id = ? AND d.usuario_id = ?
        ''', (id, user_id)).fetchone()
        
        if not despesa or not despesa['cartao_id']:
            conn.close()
            return jsonify({'is_cartao': False})

        # Data de vencimento (data_inicio)
        vencimento = datetime.strptime(despesa['data_inicio'], '%Y-%m-%d')
        mes = vencimento.month
        ano = vencimento.year
        
        status_atual = despesa['pago']
        
        # Buscar outras despesas da MESMA INSTITUIÇÃO e MESMO MÊS DE VENCIMENTO com MESMO STATUS
        # Nota: A despesa pode ser de cartões DIFERENTES, mas da MESMA INSTITUIÇÃO (ex: 2 Nubanks virtuais)
        
        query = '''
            SELECT COUNT(*) as qtd, SUM(d.valor) as total
            FROM despesa d
            JOIN cartao_credito c ON d.cartao_id = c.id
            WHERE d.usuario_id = ? 
              AND c.instituicao_id = ? 
              AND strftime('%m', d.data_inicio) = ? 
              AND strftime('%Y', d.data_inicio) = ?
              AND d.pago = ?
              AND d.id != ?
        '''
        
        resultado = conn.execute(query, (
            user_id, 
            despesa['instituicao_id'], 
            f'{mes:02d}', 
            str(ano), 
            status_atual,
            id
        )).fetchone()
        
        qtd_pendentes = resultado['qtd']
        valor_pendente = resultado['total'] or 0
        
        conn.close()
        
        if qtd_pendentes > 0:
            return jsonify({
                'is_cartao': True,
                'tem_outras_pendentes': True,
                'qtd': qtd_pendentes,
                'valor_total': valor_pendente + despesa['valor'], # Soma a atual também para contexto
                'instituicao_nome': despesa['instituicao_nome'],
                'mes_referencia': f"{mes:02d}/{ano}"
            })
            
        return jsonify({'is_cartao': True, 'tem_outras_pendentes': False})

    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@despesas_bp.route('/')
@login_required
def index():
    user_id = get_current_user_id()
    conn = get_db_connection()
    
    # Obter parâmetros de filtro
    categoria = request.args.get('categoria')
    subcategoria = request.args.get('subcategoria')
    mes = request.args.get('mes')
    ano = request.args.get('ano')

    # Default para o mês atual se não houver filtros de data (primeiro acesso)
    if mes is None and ano is None:
        hoje = datetime.now()
        mes = str(hoje.month)
        ano = str(hoje.year)
    
    # Construir query com filtros
    query = '''
        SELECT d.*, cd.nome as categoria_nome, sd.nome as subcategoria_nome,
               cc.nome_cartao as cartao_nome, cc.ultimos_digitos as cartao_digitos
        FROM despesa d
        JOIN categoria_despesa cd ON d.categoria_id = cd.id
        LEFT JOIN subcategoria_despesa sd ON d.subcategoria_id = sd.id
        LEFT JOIN cartao_credito cc ON d.cartao_id = cc.id
        WHERE d.usuario_id = ?
    '''
    
    params = [user_id]
    
    if categoria:
        query += " AND d.categoria_id = ?"
        params.append(categoria)
    
    if subcategoria:
        query += " AND d.subcategoria_id = ?"
        params.append(subcategoria)
    
    if mes:
        query += " AND strftime('%m', d.data_inicio) = ?"
        params.append(f"{int(mes):02d}")
    
    if ano:
        query += " AND strftime('%Y', d.data_inicio) = ?"
        params.append(str(ano))
    
    query += " ORDER BY d.data_inicio DESC"
    
    despesas = conn.execute(query, params).fetchall()
    
    # Converter Row objects para dicionários e converter datas
    despesas_formatadas = []
    total_valor = 0
    maior_valor = 0
    
    for despesa in despesas:
        despesa_dict = dict(despesa)
        if despesa_dict['data_inicio']:
            try:
                despesa_dict['data_inicio'] = datetime.strptime(despesa_dict['data_inicio'], '%Y-%m-%d')
            except:
                despesa_dict['data_inicio'] = None
        if despesa_dict.get('data_fim'):
            try:
                despesa_dict['data_fim'] = datetime.strptime(despesa_dict['data_fim'], '%Y-%m-%d')
            except:
                despesa_dict['data_fim'] = None
        
        # Calcular estatísticas
        valor = float(despesa_dict.get('valor', 0))
        total_valor += valor
        if valor > maior_valor:
            maior_valor = valor
            
        despesas_formatadas.append(type('obj', (object,), despesa_dict))
    
    # Calcular média
    media_valor = total_valor / len(despesas_formatadas) if despesas_formatadas else 0
    
    # Obter categorias para o filtro
    categorias = get_categorias_despesas(usuario_id=user_id)
    
    # Preparar estatísticas
    estatisticas = {
        'total': len(despesas_formatadas),
        'valor_total': total_valor,
        'media_valor': media_valor,
        'maior_valor': maior_valor
    }
    
    conn.close()
    return render_template('despesas/index.html', 
                           despesas=despesas_formatadas, 
                           categorias=categorias, 
                           stats=estatisticas,
                           mes_selecionado=mes,
                           ano_selecionado=ano)

@despesas_bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    user_id = get_current_user_id()
    if request.method == 'POST':
        categoria_id = request.form['categoria_id']
        subcategoria_id = request.form.get('subcategoria_id') or None
        data_inicio = request.form['data_inicio']
        data_fim = request.form.get('data_fim') or None
        tipo_recorrencia = request.form['tipo_recorrencia']
        dia_comum = request.form.get('dia_comum_pagamento')
        valor_parcela = request.form['valor_parcela']
        fixo = bool(request.form.get('fixo'))  # Checkbox para despesa fixa
        cartao_id = request.form.get('cartao_id') or None
        
        # Lógica de Compra Parcelada Checkbox
        compra_parcelada_check = request.form.get('compra_parcelada') == '1'
        
        if compra_parcelada_check:
            # Inputs específicos
            valor_total_bem = request.form.get('valor_total_bem')
            qtd_parcelas_input = request.form.get('qtd_parcelas_input')
            mes_primeira_fatura = request.form.get('mes_primeira_fatura')  # YYYY-MM
            
            if not valor_total_bem or not qtd_parcelas_input or not mes_primeira_fatura:
                flash('Para compra parcelada, preencha valor total, nº de parcelas e 1ª fatura.', 'error')
                return redirect(url_for('despesas.nova'))
            
            if not cartao_id:
                flash('Compra parcelada exige um cartão de crédito selecionado.', 'error')
                return redirect(url_for('despesas.nova'))
                
            try:
                # Tratar valor total
                if ',' in valor_total_bem:
                    valor_total_bem = valor_total_bem.replace('.', '').replace(',', '.')
                valor_total_bem = float(valor_total_bem)
                
                qtd_parcelas = int(qtd_parcelas_input)
                
                if qtd_parcelas <= 1:
                     flash('Para compra parcelada, o número de parcelas deve ser maior que 1.', 'error')
                     return redirect(url_for('despesas.nova'))
                     
                # Calcular valor da parcela
                valor_parcela = valor_total_bem / qtd_parcelas
                
                # Definir recorrência
                tipo_recorrencia = 'mensal'
                fixo = False
                dia_comum = None  # Será definido pelo vencimento do cartão
                
                # Calcular Data de Início baseada no mês da primeira fatura e vencimento do cartão
                conn = get_db_connection()
                cartao = conn.execute('SELECT dia_vencimento FROM cartao_credito WHERE id = ?', (cartao_id,)).fetchone()
                conn.close()
                
                if not cartao:
                    flash('Cartão não encontrado.', 'error')
                    return redirect(url_for('despesas.nova'))
                    
                dia_vencimento = cartao['dia_vencimento']
                ano_fatura, mes_fatura = map(int, mes_primeira_fatura.split('-'))
                
                try:
                    data_inicio_obj = datetime(ano_fatura, mes_fatura, dia_vencimento).date()
                except ValueError:
                    # Caso dia de vencimento (ex: 31) não exista no mês, pega o último dia
                    ultimo_dia = (datetime(ano_fatura, mes_fatura, 1) + relativedelta(months=1) - relativedelta(days=1)).day
                    data_inicio_obj = datetime(ano_fatura, mes_fatura, ultimo_dia).date()
                
                data_inicio = data_inicio_obj.strftime('%Y-%m-%d')
                
                # Calcular Data de Fim para gerar exatamente X parcelas
                # data_fim = data_inicio + (qtd - 1) meses
                data_fim_obj = data_inicio_obj + relativedelta(months=qtd_parcelas - 1)
                data_fim = data_fim_obj.strftime('%Y-%m-%d')
                
                flash(f'Compra parcelada configurada: 1ª parc. em {data_inicio} (Total: {qtd_parcelas}x)', 'info')
                
            except ValueError:
                flash('Valores inválidos para compra parcelada.', 'error')
                return redirect(url_for('despesas.nova'))

        else:
            # Lógica Padrão (Manter código existente)
            # Validações normais
            if not categoria_id or not data_inicio or not tipo_recorrencia or not valor_parcela:
                flash('Categoria, data de início, tipo de recorrência e valor por parcela são obrigatórios.', 'error')
                return redirect(url_for('despesas.nova'))
            
            try:
                # Converter valor: se tem vírgula, tratar como separador decimal brasileiro
                if ',' in valor_parcela:
                    valor_parcela = valor_parcela.replace('.', '').replace(',', '.')
                valor_parcela = float(valor_parcela)
                if valor_parcela <= 0:
                    flash('O valor deve ser maior que zero.', 'error')
                    return redirect(url_for('despesas.nova'))
            except ValueError:
                flash('Valor inválido.', 'error')
                return redirect(url_for('despesas.nova'))
            
            # Converter dia comum para inteiro se fornecido
            if dia_comum:
                try:
                    dia_comum = int(dia_comum)
                    if dia_comum < 1 or dia_comum > 31:
                        flash('Dia comum deve estar entre 1 e 31.', 'error')
                        return redirect(url_for('despesas.nova'))
                except ValueError:
                    dia_comum = None
            else:
                dia_comum = None

            # Lógica de Cartão de Crédito (Cálculo automático de vencimento)
            if cartao_id:
                conn = get_db_connection()
                cartao = conn.execute('SELECT dia_fechamento, dia_vencimento FROM cartao_credito WHERE id = ?', (cartao_id,)).fetchone()
                conn.close()

                if cartao:
                    dia_fechamento = cartao['dia_fechamento']
                    dia_vencimento = cartao['dia_vencimento']
                    
                    # Converter data da compra
                    data_compra_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                    
                    # Calcular data de fechamento para o mês da compra
                    try:
                        data_fechamento_mes = data_compra_obj.replace(day=dia_fechamento)
                    except ValueError:
                        ultimo_dia = (data_compra_obj + relativedelta(day=31)).day
                        data_fechamento_mes = data_compra_obj.replace(day=ultimo_dia)

                    # Definir data de vencimento base
                    if data_compra_obj < data_fechamento_mes:
                        data_base_vencimento = data_compra_obj
                    else:
                        data_base_vencimento = data_compra_obj + relativedelta(months=1)
                    
                    # Ajustar para o dia de vencimento
                    try:
                        data_vencimento_real = data_base_vencimento.replace(day=dia_vencimento)
                    except ValueError:
                        ultimo_dia = (data_base_vencimento + relativedelta(day=31)).day
                        data_vencimento_real = data_base_vencimento.replace(day=ultimo_dia)
                    
                    if dia_vencimento < dia_fechamento:
                        data_vencimento_real = data_vencimento_real + relativedelta(months=1)
                    
                    data_inicio = data_vencimento_real.strftime('%Y-%m-%d')
                    
                    if tipo_recorrencia != 'unica':
                        tipo_recorrencia = 'mensal'
                        dia_comum = dia_vencimento
                        flash(f'Despesa ajustada para cartão: Vencimento em {data_inicio} (Recorrência Mensal)', 'info')
                    else:
                        flash(f'Despesa atualizada para vencimento do cartão: {data_inicio}', 'info')
        
        # Gerar parcelas
        try:
            despesa_pai_id = gerar_parcelas_despesa(
                categoria_id, subcategoria_id, data_inicio, data_fim, 
                tipo_recorrencia, valor_parcela, dia_comum, user_id, fixo,
                cartao_id=cartao_id
            )
            flash('Despesa cadastrada com sucesso!', 'success')
            return redirect(url_for('despesas.index'))
        except Exception as e:
            flash(f'Erro ao cadastrar despesa: {str(e)}', 'error')
    
    categorias = get_categorias_despesas(usuario_id=user_id)
    
    # Para nova despesa, carregar subcategorias da primeira categoria se existir
    subcategorias = []
    if categorias:
        primeira_categoria_id = categorias[0]['id']
        subcategorias = get_subcategorias_despesas(categoria_id=primeira_categoria_id, usuario_id=user_id)
    
    cartoes = get_cartoes_credito(user_id)
    return render_template('despesas/form.html', categorias=categorias, subcategorias=subcategorias, despesa=None, cartoes=cartoes)

@despesas_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    
    if request.method == 'POST':
        # Preparação para edição em lote: capturar estado anterior
        scope = request.form.get('scope')
        despesa_result = conn.execute('SELECT * FROM despesa WHERE id = ?', (id,)).fetchone()
        despesa_antiga = dict(despesa_result) if despesa_result else None
        categoria_id = request.form['categoria_id']
        subcategoria_id = request.form.get('subcategoria_id') or None
        data_inicio = request.form['data_inicio']
        valor = request.form['valor'].replace(',', '.')
        fixo = request.form.get('fixo') == 'on' or request.form.get('fixo') == '1'
        cartao_id = request.form.get('cartao_id') or None

        # Calcular diferença de dias para ajuste em lote (se necessário)
        delta_days = 0
        if scope == 'future' and despesa_antiga and data_inicio:
            try:
                dt_nova = datetime.strptime(data_inicio, '%Y-%m-%d')
                dt_antiga = datetime.strptime(despesa_antiga['data_inicio'], '%Y-%m-%d')
                delta_days = (dt_nova - dt_antiga).days
            except ValueError:
                pass

        
        # Validações
        if not categoria_id or not data_inicio or not valor:
            flash('Categoria, data e valor são obrigatórios.', 'error')
            return redirect(url_for('despesas.editar', id=id))
        
        try:
            # Converter valor: se tem vírgula, tratar como separador decimal brasileiro
            if ',' in valor:
                valor = valor.replace('.', '').replace(',', '.')
            valor = float(valor)
            if valor <= 0:
                flash('O valor deve ser maior que zero.', 'error')
                return redirect(url_for('despesas.editar', id=id))
        except ValueError:
            flash('Valor inválido.', 'error')
            return redirect(url_for('despesas.editar', id=id))
        
        try:
            # Lógica de Cartão de Crédito
            if cartao_id:
                # Buscar dados do cartão (se mudou ou se é uma nova associação)
                cartao = conn.execute('SELECT dia_fechamento, dia_vencimento FROM cartao_credito WHERE id = ?', (cartao_id,)).fetchone()

                if cartao:
                    dia_fechamento = cartao['dia_fechamento']
                    dia_vencimento = cartao['dia_vencimento']
                    
                    # Converter data da compra (data_inicio vinda do form)
                    data_compra_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                    
                    # Calcular data de fechamento para o mês da compra
                    try:
                        data_fechamento_mes = data_compra_obj.replace(day=dia_fechamento)
                    except ValueError:
                        ultimo_dia = (data_compra_obj + relativedelta(day=31)).day
                        data_fechamento_mes = data_compra_obj.replace(day=ultimo_dia)

                    # Definir data de vencimento base
                    if data_compra_obj < data_fechamento_mes:
                        # Compra ANTES do fechamento do mês
                        data_base_vencimento = data_compra_obj
                    else:
                        # Compra DEPOIS do fechamento: próxima fatura
                        data_base_vencimento = data_compra_obj + relativedelta(months=1)
                    
                    # Ajustar para o dia de vencimento
                    try:
                        data_vencimento_real = data_base_vencimento.replace(day=dia_vencimento)
                    except ValueError:
                        ultimo_dia = (data_base_vencimento + relativedelta(day=31)).day
                        data_vencimento_real = data_base_vencimento.replace(day=ultimo_dia)
                    
                    # Se dia_vencimento < dia_fechamento, o vencimento é no mês SEGUINTE ao da referência da fatura
                    if dia_vencimento < dia_fechamento:
                        data_vencimento_real = data_vencimento_real + relativedelta(months=1)
                    
                    # Atualizar data_inicio para ser a data do vencimento
                    # Nota: Ao editar, se o usuário NÃO mexeu na data, ela já pode estar como vencimento.
                    # Mas como não sabemos se o que veio no form é data de compra ou vencimento anterior,
                    # e o requisito é "ter a data de pagamento do cartão", recalculamos sempre baseados no input.
                    # Risco: Se usuário abre uma despesa que já é 20/02 (vencimento) e salva mantendo 20/02, 
                    # o sistema vai achar que COMPROU dia 20/02. Se fechamento for dia 25, vai manter 20/02?
                    # Ex: Fecha 25, Vence 05 (mês seg). Compra 20/02.
                    # Recalc: Compra 20/02 < Fecha 25/02 -> Fatura Fev -> Vence 05/03.
                    # O sistema mudaria de 20/02 para 05/03? Não, mudaria a data da despesa.
                    # SE a despesa já estava salva como 05/03.
                    # Usuario abre form. Data Inicio = 05/03.
                    # Salva.
                    # Recalc: Compra 05/03. Fecha 25/03. Compra < Fecha. Fatura Mar -> Vence 05/04.
                    # ERRO: A cada salvamento a data pularia 1 mês se o vencimento for usado como entrada.
                    
                    # CORREÇÃO CRÍTICA:
                    # Precisamos saber se a data de início foi ALTERADA ou se estamos apenas associando cartão.
                    # Ou assumir que o campo no form SEMPRE deve ser a data da compra quando tem cartão?
                    # Mas no form, o value é `despesa.data_inicio`.
                    
                    # Solução: Infelizmente, o modelo de dados simples (1 campo de data) tem essa limitação.
                    # Se eu recalcular sempre, vou empurrar a data para frente em edições sucessivas.
                    # Como mitigar?
                    # (1) Só recalcular se for NOVA despesa.
                    # (2) Na edição, não recalcular a data automaticamente A MENOS QUE o usuário mude o cartão?
                    # O usuário disse: "quando eu selecionar um cartão ... a despesa vai ter a data de pagamento".
                    # Vou assumir que isso é primordialmente para NOVAS despesas.
                    # Para EDIÇÃO, é perigoso mudar a data automaticamente sem saber se o usuário inputou data de compra ou vencimento.
                    
                    # Vou manter a lógica apenas se cartao_id mudou ou se o usuário estiver criando nova.
                    # Mas no stateless HTTP post, não sei se mudou.
                    # Vou comentar a lógica de data na edição e aplicar apenas na CRIAÇÃO para evitar o bug de "empurrar data".
                    # OU, melhor: Na edição, se tiver cartão, NÃO altero data_inicio, apenas salvo.
                    # Mas e se ele mudar a data da compra na edição?
                    
                    # Vamos simplificar: Aplicar APENAS na criação (rota nova).
                    # Na edição, confiamos que o usuário ou manteve a data certa, ou editou manualmente.
                    # O risco de corromper dados existentes é alto.
                    pass 

            conn.execute('''
                UPDATE despesa 
                SET categoria_id = ?, subcategoria_id = ?, data_inicio = ?, valor = ?, fixo = ?, cartao_id = ?
                WHERE id = ?
            ''', (categoria_id, subcategoria_id, data_inicio, valor, fixo, cartao_id, id))
            
            # Edição em Lote (apenas se solicitado e possível)
            # Edição em Lote (apenas se solicitado e possível)
            if scope == 'future' and despesa_antiga and despesa_antiga['tipo_recorrencia'] != 'unica':
                # Construir query dinamicamente para incluir ajuste de data se necessário
                sql = '''UPDATE despesa SET categoria_id = ?, subcategoria_id = ?, valor = ?, fixo = ?, cartao_id = ?'''
                params = [categoria_id, subcategoria_id, valor, fixo, cartao_id]
                
                if delta_days != 0:
                    sql += ", data_inicio = date(data_inicio, ?)"
                    params.append(f'{delta_days:+} days')
                
                sql += '''
                    WHERE usuario_id = ?
                      AND categoria_id = ? 
                      AND (subcategoria_id = ? OR (subcategoria_id IS NULL AND ? IS NULL))
                      AND tipo_recorrencia = ? 
                      AND valor = ?
                      AND data_inicio > ?
                      AND datetime(created_at) BETWEEN datetime(?, '-120 seconds') AND datetime(?, '+120 seconds')
                '''
                
                params.extend([
                    user_id,
                    despesa_antiga['categoria_id'], 
                    despesa_antiga['subcategoria_id'], despesa_antiga['subcategoria_id'],
                    despesa_antiga['tipo_recorrencia'],
                    despesa_antiga['valor'],
                    despesa_antiga['data_inicio'],
                    despesa_antiga['created_at'], despesa_antiga['created_at']
                ])
                
                conn.execute(sql, params)
                
                alteradas = conn.total_changes
                if alteradas > 1:
                    flash(f'Despesa atual e {alteradas-1} futuras foram atualizadas!', 'success')
                else:
                    flash('Despesa atualizada com sucesso!', 'success')
            else:
                flash('Despesa atualizada com sucesso!', 'success')
            
            conn.commit()
            return redirect(url_for('despesas.index'))
        except Exception as e:
            flash(f'Erro ao atualizar despesa: {str(e)}', 'error')
        finally:
            conn.close()
    
    # GET - carregar dados para edição
    despesa = conn.execute('''
        SELECT d.*, cd.nome as categoria_nome, sd.nome as subcategoria_nome
        FROM despesa d
        JOIN categoria_despesa cd ON d.categoria_id = cd.id
        LEFT JOIN subcategoria_despesa sd ON d.subcategoria_id = sd.id
        WHERE d.id = ?
    ''', (id,)).fetchone()
    
    if not despesa:
        flash('Despesa não encontrada.', 'error')
        conn.close()
        return redirect(url_for('despesas.index'))
    
    categorias = get_categorias_despesas(usuario_id=user_id)
    subcategorias = get_subcategorias_despesas(despesa['categoria_id'], usuario_id=user_id)
    cartoes = get_cartoes_credito(user_id)
    conn.close()
    
    return render_template('despesas/form.html', categorias=categorias, subcategorias=subcategorias, despesa=despesa, cartoes=cartoes)

@despesas_bp.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir(id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    try:
        scope = request.form.get('scope')
        
        if scope == 'future':
            # Buscar dados da despesa original para encontrar correlatas
            despesa = conn.execute('SELECT * FROM despesa WHERE id = ?', (id,)).fetchone()
            
            if despesa and despesa['tipo_recorrencia'] != 'unica':
                # Excluir esta e as futuras com base em similaridade e data de criação (lote)
                # Janela de 2 minutos no created_at para pegar o lote gerado junto
                conn.execute('''
                    DELETE FROM despesa 
                    WHERE usuario_id = ?
                      AND categoria_id = ? 
                      AND (subcategoria_id = ? OR (subcategoria_id IS NULL AND ? IS NULL))
                      AND tipo_recorrencia = ? 
                      AND valor = ?
                      AND data_inicio >= ?
                      AND datetime(created_at) BETWEEN datetime(?, '-120 seconds') AND datetime(?, '+120 seconds')
                ''', (
                    user_id,
                    despesa['categoria_id'], 
                    despesa['subcategoria_id'], despesa['subcategoria_id'],
                    despesa['tipo_recorrencia'],
                    despesa['valor'],
                    despesa['data_inicio'],
                    despesa['created_at'], despesa['created_at']
                ))
                flash('Esta e as próximas despesas da série foram excluídas!', 'success')
            else:
                 # Fallback se não for recorrente ou não achar
                 conn.execute('DELETE FROM despesa WHERE id = ?', (id,))
                 flash('Despesa excluída com sucesso!', 'success')
        else:
            # Excluir apenas a despesa individual
            conn.execute('DELETE FROM despesa WHERE id = ?', (id,))
            flash('Despesa excluída com sucesso!', 'success')
            
        conn.commit()
    except Exception as e:
        flash(f'Erro ao excluir despesa: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('despesas.index'))

@despesas_bp.route('/subcategorias/<int:categoria_id>')
@login_required
def subcategorias(categoria_id):
    user_id = get_current_user_id()
    subcategorias = get_subcategorias_despesas(categoria_id, usuario_id=user_id)
    return jsonify([{'id': sub['id'], 'nome': sub['nome']} for sub in subcategorias])
