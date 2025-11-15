#!/usr/bin/env python3
"""
모든 DB의 스키마 정보를 미리 수집하여 JSON 파일로 저장합니다.
이 파일을 실행하면 모든 테이블과 컬럼 정보가 캐시됩니다.
"""

import json
import os
import sqlite3
from typing import Dict, Set, List

# PostgreSQL 지원
try:
    import psycopg
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False
    print("Warning: psycopg가 설치되지 않았습니다. PostgreSQL 기능을 사용할 수 없습니다.")

from db_config import DB_CONFIGS

def get_tables_sqlite(conn) -> Set[str]:
    """SQLite에서 테이블 목록 가져오기"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    results = cursor.fetchall()
    cursor.close()
    return {row[0] for row in results}

def get_table_info_sqlite(conn, table_name: str) -> Dict:
    """SQLite에서 테이블의 컬럼, PK, FK 정보 가져오기"""
    cursor = conn.cursor()
    
    # 컬럼 및 PK 정보
    cursor.execute(f"PRAGMA table_info({table_name})")
    table_info = cursor.fetchall()
    # PRAGMA table_info 결과: (cid, name, type, notnull, default_value, pk)
    columns = [row[1] for row in table_info]
    primary_keys = [row[1] for row in table_info if row[5] == 1]  # pk=1인 컬럼들
    
    # FK 정보
    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
    fk_info = cursor.fetchall()
    # PRAGMA foreign_key_list 결과: (id, seq, table, from, to, on_update, on_delete, match)
    foreign_keys = []
    for fk in fk_info:
        foreign_keys.append({
            "column": fk[3],  # from
            "references_table": fk[2],  # table
            "references_column": fk[4]  # to
        })
    
    cursor.close()
    
    return {
        "columns": columns,
        "primary_keys": primary_keys,
        "foreign_keys": foreign_keys
    }

def get_tables_postgresql(conn, schema: str) -> Set[str]:
    """PostgreSQL에서 테이블 목록 가져오기"""
    query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = %s
    """
    results = conn.execute(query, (schema,)).fetchall()
    return {row[0] for row in results}

def get_table_info_postgresql(conn, schema: str, table_name: str) -> Dict:
    """PostgreSQL에서 테이블의 컬럼, PK, FK 정보 가져오기"""
    # 컬럼 정보
    query = """
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_schema = %s AND table_name = %s
    ORDER BY ordinal_position
    """
    results = conn.execute(query, (schema, table_name)).fetchall()
    columns = [row[0] for row in results]
    
    # PK 정보
    pk_query = """
    SELECT kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY'
        AND tc.table_schema = %s
        AND tc.table_name = %s
    ORDER BY kcu.ordinal_position
    """
    pk_results = conn.execute(pk_query, (schema, table_name)).fetchall()
    primary_keys = [row[0] for row in pk_results]
    
    # FK 정보
    fk_query = """
    SELECT
        kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = %s
        AND tc.table_name = %s
    ORDER BY kcu.ordinal_position
    """
    fk_results = conn.execute(fk_query, (schema, table_name)).fetchall()
    foreign_keys = [
        {
            "column": row[0],
            "references_table": row[1],
            "references_column": row[2]
        }
        for row in fk_results
    ]
    
    return {
        "columns": columns,
        "primary_keys": primary_keys,
        "foreign_keys": foreign_keys
    }

def build_schema_cache() -> Dict[str, Dict[str, Dict]]:
    """
    모든 DB의 스키마 정보를 수집합니다.
    반환: {db_name: {table_name: {columns: [...], primary_keys: [...], foreign_keys: [...]}}}
    """
    schema_cache = {}
    
    for db_name, config in DB_CONFIGS.items():
        print(f"\n처리 중: {db_name} ({config['type']})")
        db_schema = {}
        
        try:
            if config["type"] == "sqlite":
                if not os.path.exists(config["path"]):
                    print(f"  ⚠️  파일을 찾을 수 없습니다: {config['path']}")
                    continue
                
                conn = sqlite3.connect(config["path"])
                tables = get_tables_sqlite(conn)
                
                for table_name in tables:
                    table_info = get_table_info_sqlite(conn, table_name)
                    db_schema[table_name] = table_info
                    pk_info = f", PK: {len(table_info['primary_keys'])}개" if table_info['primary_keys'] else ""
                    fk_info = f", FK: {len(table_info['foreign_keys'])}개" if table_info['foreign_keys'] else ""
                    print(f"  ✓ {table_name}: {len(table_info['columns'])}개 컬럼{pk_info}{fk_info}")
                
                conn.close()
                
            elif config["type"] == "postgresql":
                if not PSYCOPG_AVAILABLE:
                    print(f"  ⚠️  psycopg가 설치되지 않았습니다.")
                    continue
                
                schema = config.get("schema", "public")
                conn = psycopg.connect(config["url"])
                tables = get_tables_postgresql(conn, schema)
                
                for table_name in tables:
                    table_info = get_table_info_postgresql(conn, schema, table_name)
                    db_schema[table_name] = table_info
                    pk_info = f", PK: {len(table_info['primary_keys'])}개" if table_info['primary_keys'] else ""
                    fk_info = f", FK: {len(table_info['foreign_keys'])}개" if table_info['foreign_keys'] else ""
                    print(f"  ✓ {table_name}: {len(table_info['columns'])}개 컬럼{pk_info}{fk_info}")
                
                conn.close()
            else:
                print(f"  ⚠️  지원하지 않는 DB 타입: {config['type']}")
                continue
            
            schema_cache[db_name] = db_schema
            print(f"  ✅ 완료: {len(tables)}개 테이블")
            
        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return schema_cache

def main():
    """메인 함수"""
    print("=" * 60)
    print("DB 스키마 캐시 빌드 시작")
    print("=" * 60)
    
    schema_cache = build_schema_cache()
    
    # JSON 파일로 저장
    output_file = "data/schema_cache.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(schema_cache, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print(f"✅ 스키마 캐시 저장 완료: {output_file}")
    print(f"   총 {len(schema_cache)}개 DB 처리됨")
    
    # 통계 출력
    total_tables = sum(len(tables) for tables in schema_cache.values())
    total_columns = sum(
        sum(len(table_info['columns']) for table_info in tables.values())
        for tables in schema_cache.values()
    )
    total_pks = sum(
        sum(len(table_info['primary_keys']) for table_info in tables.values())
        for tables in schema_cache.values()
    )
    total_fks = sum(
        sum(len(table_info['foreign_keys']) for table_info in tables.values())
        for tables in schema_cache.values()
    )
    print(f"   총 {total_tables}개 테이블, {total_columns}개 컬럼")
    print(f"   총 {total_pks}개 PK, {total_fks}개 FK")
    print("=" * 60)

if __name__ == "__main__":
    main()

