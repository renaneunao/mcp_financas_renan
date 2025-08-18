#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para marcar despesas e receitas específicas como fixas
"""

import sqlite3
from app.database import get_db_connection

def marcar_despesas_como_fixas():
    """Marca despesas específicas como fixas baseado na categoria ou subcategoria"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Lista de despesas para marcar como fixas
    despesas_fixas = [
        "Fies",
        "Alimentação", 
        "Telefonia",
        "Despesas de Contracheque",
        "Academia"
    ]
    
    print("🔍 Procurando despesas para marcar como fixas...")
    
    for nome in despesas_fixas:
        # Buscar por categoria
        cursor.execute("""
            SELECT d.id, cd.nome as categoria, sd.nome as subcategoria, d.valor, d.data_inicio
            FROM despesa d
            JOIN categoria_despesa cd ON d.categoria_id = cd.id
            LEFT JOIN subcategoria_despesa sd ON d.subcategoria_id = sd.id
            WHERE cd.nome LIKE ? OR sd.nome LIKE ?
        """, (f"%{nome}%", f"%{nome}%"))
        
        despesas_encontradas = cursor.fetchall()
        
        if despesas_encontradas:
            print(f"\n📋 Encontradas {len(despesas_encontradas)} despesas com '{nome}':")
            for despesa in despesas_encontradas:
                print(f"  ID: {despesa['id']} | {despesa['categoria']} > {despesa['subcategoria']} | R$ {despesa['valor']:.2f} | {despesa['data_inicio']}")
            
            # Marcar como fixas
            ids = [str(despesa['id']) for despesa in despesas_encontradas]
            placeholders = ','.join(['?'] * len(ids))
            cursor.execute(f"UPDATE despesa SET fixo = 1 WHERE id IN ({placeholders})", ids)
            print(f"✅ {len(despesas_encontradas)} despesas marcadas como fixas!")
        else:
            print(f"❌ Nenhuma despesa encontrada com '{nome}'")
    
    conn.commit()
    return cursor.rowcount

def marcar_receitas_como_fixas():
    """Marca receitas específicas como fixas baseado na categoria ou subcategoria"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Lista de receitas para marcar como fixas
    receitas_fixas = [
        "Relatório Summit",
        "Salário",
        "Vale Alimentação", 
        "Anuênio"
    ]
    
    print("\n🔍 Procurando receitas para marcar como fixas...")
    
    for nome in receitas_fixas:
        # Buscar por categoria ou subcategoria
        cursor.execute("""
            SELECT r.id, cr.nome as categoria, sr.nome as subcategoria, r.valor, r.data_inicio
            FROM receita r
            JOIN categoria_receita cr ON r.categoria_id = cr.id
            LEFT JOIN subcategoria_receita sr ON r.subcategoria_id = sr.id
            WHERE cr.nome LIKE ? OR sr.nome LIKE ?
        """, (f"%{nome}%", f"%{nome}%"))
        
        receitas_encontradas = cursor.fetchall()
        
        if receitas_encontradas:
            print(f"\n📋 Encontradas {len(receitas_encontradas)} receitas com '{nome}':")
            for receita in receitas_encontradas:
                print(f"  ID: {receita['id']} | {receita['categoria']} > {receita['subcategoria']} | R$ {receita['valor']:.2f} | {receita['data_inicio']}")
            
            # Marcar como fixas
            ids = [str(receita['id']) for receita in receitas_encontradas]
            placeholders = ','.join(['?'] * len(ids))
            cursor.execute(f"UPDATE receita SET fixo = 1 WHERE id IN ({placeholders})", ids)
            print(f"✅ {len(receitas_encontradas)} receitas marcadas como fixas!")
        else:
            print(f"❌ Nenhuma receita encontrada com '{nome}'")
    
    conn.commit()
    return cursor.rowcount

def verificar_resultados():
    """Verifica quais itens foram marcados como fixos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("\n📊 RESUMO - Despesas marcadas como fixas:")
    cursor.execute("""
        SELECT d.id, cd.nome as categoria, sd.nome as subcategoria, d.valor, d.data_inicio
        FROM despesa d
        JOIN categoria_despesa cd ON d.categoria_id = cd.id
        LEFT JOIN subcategoria_despesa sd ON d.subcategoria_id = sd.id
        WHERE d.fixo = 1
        ORDER BY cd.nome, sd.nome
    """)
    
    despesas_fixas = cursor.fetchall()
    for despesa in despesas_fixas:
        print(f"  🔸 {despesa['categoria']} > {despesa['subcategoria']} | R$ {despesa['valor']:.2f}")
    
    print(f"\nTotal de despesas fixas: {len(despesas_fixas)}")
    
    print("\n📊 RESUMO - Receitas marcadas como fixas:")
    cursor.execute("""
        SELECT r.id, cr.nome as categoria, sr.nome as subcategoria, r.valor, r.data_inicio
        FROM receita r
        JOIN categoria_receita cr ON r.categoria_id = cr.id
        LEFT JOIN subcategoria_receita sr ON r.subcategoria_id = sr.id
        WHERE r.fixo = 1
        ORDER BY cr.nome, sr.nome
    """)
    
    receitas_fixas = cursor.fetchall()
    for receita in receitas_fixas:
        print(f"  🔸 {receita['categoria']} > {receita['subcategoria']} | R$ {receita['valor']:.2f}")
    
    print(f"\nTotal de receitas fixas: {len(receitas_fixas)}")
    
    conn.close()

if __name__ == "__main__":
    print("🚀 Iniciando script para marcar itens como fixos...")
    
    try:
        # Marcar despesas como fixas
        despesas_atualizadas = marcar_despesas_como_fixas()
        
        # Marcar receitas como fixas
        receitas_atualizadas = marcar_receitas_como_fixas()
        
        # Verificar resultados
        verificar_resultados()
        
        print(f"\n✅ Script concluído com sucesso!")
        print(f"   Total de itens atualizados: {despesas_atualizadas + receitas_atualizadas}")
        
    except Exception as e:
        print(f"❌ Erro ao executar script: {e}")
