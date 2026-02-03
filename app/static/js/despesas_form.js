// Funções de UI e Comportamento

function toggleRecurrenceFields(tipoRecorrencia) {
    const dataFimField = document.getElementById('data_fim_field');
    const diaComumField = document.getElementById('dia_comum_field');
    const valorLabel = document.querySelector('label[for="valor_parcela"]');
    const valorHelp = document.querySelector('#valor_parcela').nextElementSibling;
    const cartaoSelect = document.getElementById('cartao_id');
    const temCartao = cartaoSelect && cartaoSelect.value;

    if (tipoRecorrencia === 'unica') {
        if (dataFimField) dataFimField.style.display = 'none';
        if (diaComumField) diaComumField.style.display = 'none';

        if (valorLabel) valorLabel.innerHTML = '<i class="fas fa-dollar-sign text-red-400 mr-2"></i>Valor da Despesa *';
        if (valorHelp) valorHelp.textContent = 'Valor total desta despesa específica';
    } else {
        if (dataFimField) dataFimField.style.display = 'block';
        if (diaComumField) diaComumField.style.display = temCartao ? 'none' : 'block';

        if (valorLabel) valorLabel.innerHTML = '<i class="fas fa-dollar-sign text-red-400 mr-2"></i>Valor por Parcela *';
        if (valorHelp) valorHelp.textContent = 'Este será o valor de cada parcela gerada (ex: aluguel mensal)';
    }
}

function updateSubcategorias(categoriaId, targetId) {
    if (!categoriaId) {
        document.getElementById(targetId).innerHTML = '<option value="" class="bg-gray-800">Selecione uma subcategoria (opcional)</option>';
        return;
    }

    fetch(`/despesas/subcategorias/${categoriaId}`)
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById(targetId);
            select.innerHTML = '<option value="" class="bg-gray-800">Selecione uma subcategoria (opcional)</option>';
            data.forEach(subcategoria => {
                const option = document.createElement('option');
                option.value = subcategoria.id;
                option.textContent = subcategoria.nome;
                option.className = 'bg-gray-800';
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Erro ao buscar subcategorias:', error));
}

function toggleCartaoInfo(cartaoId) {
    const dataLabel = document.querySelector('label[for="data_inicio"]');
    const helpText = document.getElementById('cartao_help_text');
    const tipoRecorrencia = document.getElementById('tipo_recorrencia');
    const compraParceladaContainer = document.getElementById('compra_parcelada_container');

    if (cartaoId) {
        dataLabel.innerHTML = '<i class="fas fa-shopping-cart text-red-400 mr-1.5"></i>Data da Compra *';
        if (!helpText) {
            const p = document.createElement('p');
            p.id = 'cartao_help_text';
            p.className = 'text-[10px] text-yellow-500 mt-1';
            p.innerHTML = '<i class="fas fa-info-circle mr-1"></i>O vencimento será calculado automaticamente conforme a fatura.';
            document.getElementById('data_inicio').parentNode.appendChild(p);
        }
        // Show Compra Parcelada option
        if (compraParceladaContainer) {
            compraParceladaContainer.classList.remove('hidden');
            compraParceladaContainer.style.display = 'block';
        }
    } else {
        dataLabel.innerHTML = '<i class="fas fa-calendar text-red-400 mr-1.5"></i>Data de Início *';
        if (helpText) helpText.remove();

        // Hide Compra Parcelada and reset
        if (compraParceladaContainer) {
            compraParceladaContainer.classList.add('hidden');
            compraParceladaContainer.style.display = 'none';
            const checkbox = document.getElementById('compra_parcelada');
            if (checkbox && checkbox.checked) {
                checkbox.checked = false;
                toggleCompraParcelada(false);
            }
        }
    }

    if (tipoRecorrencia) {
        toggleRecurrenceFields(tipoRecorrencia.value);
    }
}

function toggleCompraParcelada(isParcelado) {
    const tipoRecorrenciaContainer = document.getElementById('tipo_recorrencia_container');
    const fixoContainer = document.getElementById('fixo_container');
    const valorContainer = document.getElementById('valor_container');
    const camposParceladosContainer = document.getElementById('campos_parcelados_container');
    const dataInicioInput = document.getElementById('data_inicio');

    // Fields to toggle required
    // Note: input ID changes based on edit mode (valor vs valor_parcela)
    const valorInput = document.getElementById('valor') || document.getElementById('valor_parcela');
    const tipoRecorrenciaInput = document.getElementById('tipo_recorrencia');

    // New fields
    const valorTotalBemInput = document.getElementById('valor_total_bem');
    const qtdParcelasInput = document.getElementById('qtd_parcelas_input');
    const mesPrimeiraFaturaInput = document.getElementById('mes_primeira_fatura');

    if (isParcelado) {
        // Hide standard fields
        if (tipoRecorrenciaContainer) tipoRecorrenciaContainer.style.display = 'none';
        if (fixoContainer) fixoContainer.style.display = 'none';
        if (valorContainer) valorContainer.style.display = 'none';
        if (dataInicioInput) dataInicioInput.closest('div').style.display = 'none';

        // Show new fields
        if (camposParceladosContainer) {
            camposParceladosContainer.classList.remove('hidden');
            camposParceladosContainer.style.display = 'block';
        }

        // Manage Required
        if (valorInput) valorInput.required = false;
        if (tipoRecorrenciaInput) tipoRecorrenciaInput.required = false;
        if (dataInicioInput) dataInicioInput.required = false;

        if (valorTotalBemInput) valorTotalBemInput.required = true;
        if (qtdParcelasInput) qtdParcelasInput.required = true;
        if (mesPrimeiraFaturaInput) mesPrimeiraFaturaInput.required = true;

    } else {
        // Show standard fields
        if (tipoRecorrenciaContainer) tipoRecorrenciaContainer.style.display = 'block';
        if (fixoContainer) fixoContainer.style.display = 'flex';
        if (valorContainer) valorContainer.style.display = 'block';
        if (dataInicioInput) {
            dataInicioInput.closest('div').style.display = 'block';
            dataInicioInput.required = true;
        }

        // Hide new fields
        if (camposParceladosContainer) {
            camposParceladosContainer.classList.add('hidden');
            camposParceladosContainer.style.display = 'none';
        }

        // Manage Required
        if (valorInput) valorInput.required = true;
        if (tipoRecorrenciaInput) tipoRecorrenciaInput.required = true;

        if (valorTotalBemInput) valorTotalBemInput.required = false;
        if (qtdParcelasInput) qtdParcelasInput.required = false;
        if (mesPrimeiraFaturaInput) mesPrimeiraFaturaInput.required = false;

        // Trigger recurrence toggle to ensure correct state of data_fim etc
        if (tipoRecorrenciaInput) toggleRecurrenceFields(tipoRecorrenciaInput.value);
    }
}

// Lógica de Submit e Exclusão (Lote)
function submitDelete(id, scope) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/despesas/excluir/' + id;

    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'scope';
    input.value = scope;
    form.appendChild(input);

    document.body.appendChild(form);
    form.submit();
}

function confirmarExclusao() {
    const ctx = window.despesaContext || {};
    console.log('Contexto de exclusão:', ctx);

    // Garantir que ID seja pego corretamente, mesmo que venha como string ou número
    const despesaId = ctx.id;

    if (!despesaId) {
        alert('Erro: ID da despesa não encontrado.');
        console.error('ID da despesa é undefined ou null', ctx);
        return;
    }

    const isRecorrente = ctx.tipoRecorrencia && ctx.tipoRecorrencia !== 'unica';

    if (!isRecorrente) {
        showConfirm('Tem certeza que deseja excluir esta despesa? Esta ação não pode ser desfeita.', function () {
            submitDelete(despesaId, 'one');
        });
        return;
    }

    showOptionDialog(
        'Excluir Despesa Recorrente',
        'Esta é uma despesa recorrente. O que deseja excluir?',
        [
            {
                text: 'Apenas Esta',
                class: 'bg-red-600 hover:bg-red-500 text-white',
                action: () => submitDelete(despesaId, 'one')
            },
            {
                text: 'Esta e as Próximas',
                class: 'bg-orange-600 hover:bg-orange-500 text-white',
                action: () => submitDelete(despesaId, 'future')
            },
            { text: 'Cancelar', class: 'bg-gray-600 hover:bg-gray-500 text-white' }
        ]
    );
}

// Inicialização e Listeners
document.addEventListener('DOMContentLoaded', function () {
    const dataInicioField = document.getElementById('data_inicio');
    const tipoRecorrenciaField = document.getElementById('tipo_recorrencia');
    const cartaoSelect = document.getElementById('cartao_id');
    const mainForm = document.querySelector('form');

    // Setup Data Inicial
    if (dataInicioField && !dataInicioField.value) {
        const hoje = new Date();
        const dataFormatada = hoje.getFullYear() + '-' +
            String(hoje.getMonth() + 1).padStart(2, '0') + '-' +
            String(hoje.getDate()).padStart(2, '0');
        dataInicioField.value = dataFormatada;
    }

    // Setup Recorrencia Inicial
    if (tipoRecorrenciaField && tipoRecorrenciaField.value === 'unica') {
        toggleRecurrenceFields('unica');
    }

    // Setup Cartao Listener
    if (cartaoSelect) {
        cartaoSelect.addEventListener('change', function () {
            toggleCartaoInfo(this.value);
        });
        // Inicializar estado (sem recursão do toggleRecurrenceFields se já foi chamado acima? nao tem problema)
        toggleCartaoInfo(cartaoSelect.value);
    }

    // Setup Compra Parcelada Listener
    const compraParceladaCheckbox = document.getElementById('compra_parcelada');
    if (compraParceladaCheckbox) {
        compraParceladaCheckbox.addEventListener('change', function () {
            toggleCompraParcelada(this.checked);
        });
    }

    // Interceptar Submit para Edição em Lote
    if (mainForm) {
        mainForm.addEventListener('submit', function (e) {
            const ctx = window.despesaContext || {};

            // Debug
            console.log('Interceptando submit. Contexto:', ctx);

            // Se não é edição ou não é recorrente, deixa passar
            if (!ctx.isEdicao || ctx.tipoRecorrencia === 'unica') return;

            // Se já tem scope, deixa passar
            if (this.querySelector('input[name="scope"]')) return;

            e.preventDefault();

            showOptionDialog(
                'Salvar Alterações',
                'Esta é uma despesa recorrente. Como deseja aplicar as alterações?',
                [
                    {
                        text: 'Apenas nesta competência',
                        class: 'bg-blue-600 hover:bg-blue-500 text-white',
                        action: () => {
                            const input = document.createElement('input');
                            input.type = 'hidden';
                            input.name = 'scope';
                            input.value = 'one';
                            this.appendChild(input);
                            this.submit();
                        }
                    },
                    {
                        text: 'Nesta e nas próximas',
                        class: 'bg-yellow-600 hover:bg-yellow-500 text-white',
                        action: () => {
                            const input = document.createElement('input');
                            input.type = 'hidden';
                            input.name = 'scope';
                            input.value = 'future';
                            this.appendChild(input);
                            this.submit();
                        }
                    },
                    { text: 'Cancelar', class: 'bg-gray-600 hover:bg-gray-500 text-white' }
                ]
            );
        });
    }
});
