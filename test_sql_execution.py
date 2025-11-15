#!/usr/bin/env python3
"""
생성된 워크로드의 SQL을 실제 DB에서 실행하여 결과를 테스트하는 스크립트
"""

import json
import sqlite3
import os
from typing import Dict, Any, List

# DB 연결 설정
DB_CONFIGS = {
    "eicu": {
        "type": "sqlite",
        "path": "/data/yhyunjun/HybridSQL-Benchmark/EHRSQL/EHRSQL/dataset/ehrsql/eicu/eicu.sqlite"
    },
    "mimic_iii": {
        "type": "sqlite",
        "path": "/data/yhyunjun/HybridSQL-Benchmark/EHRSQL/EHRSQL/dataset/ehrsql/mimic_iii/mimic_iii.sqlite"
    }
}

def get_db_connection(target_db: str):
    """데이터베이스 연결을 가져옵니다."""
    if target_db not in DB_CONFIGS:
        raise ValueError(f"지원하지 않는 데이터베이스: {target_db}")
    
    config = DB_CONFIGS[target_db]
    
    if config["type"] == "sqlite":
        if not os.path.exists(config["path"]):
            raise FileNotFoundError(f"SQLite 데이터베이스를 찾을 수 없습니다: {config['path']}")
        return sqlite3.connect(config["path"])
    else:
        raise ValueError(f"지원하지 않는 데이터베이스 타입: {config['type']}")

def execute_sql_query(target_db: str, sql_query: str) -> Dict[str, Any]:
    """SQL 쿼리를 실행하고 결과를 반환합니다."""
    try:
        conn = get_db_connection(target_db)
        cursor = conn.cursor()
        
        # SQL 실행
        cursor.execute(sql_query)
        results = cursor.fetchall()
        
        # 컬럼 정보 가져오기
        columns = [description[0] for description in cursor.description] if cursor.description else []
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "row_count": len(results),
            "columns": columns,
            "results": results[:10],  # 최대 10개 행만 저장
            "has_more": len(results) > 10
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "row_count": 0,
            "columns": [],
            "results": []
        }

def test_workload_execution(workload_file: str) -> Dict[str, Any]:
    """워크로드 파일의 모든 쿼리를 테스트합니다."""
    
    # 워크로드 파일 로드
    with open(workload_file, 'r', encoding='utf-8') as f:
        workload = json.load(f)
    
    target_db = workload["target_db"]
    queries = workload["queries"]
    
    print(f"=== 워크로드 실행 테스트 ===")
    print(f"벤치마크: {workload['benchmark_type']}")
    print(f"데이터베이스: {target_db}")
    print(f"총 쿼리 수: {len(queries)}")
    print()
    
    execution_results = []
    successful_queries = 0
    failed_queries = 0
    
    for query in queries:
        query_id = query["id"]
        sql = query["sql"]
        
        print(f"쿼리 {query_id} 실행 중...")
        print(f"SQL: {sql[:100]}...")
        
        # SQL 실행
        result = execute_sql_query(target_db, sql)
        
        if result["success"]:
            successful_queries += 1
            print(f"✅ 성공 - {result['row_count']}개 행 반환")
            if result["results"]:
                print(f"   샘플 결과: {result['results'][0]}")
        else:
            failed_queries += 1
            print(f"❌ 실패 - {result['error']}")
        
        print()
        
        # 결과 저장
        execution_results.append({
            "query_id": query_id,
            "template_id": query["template_id"],
            "question": query["question"],
            "sql": sql,
            "execution_result": result
        })
    
    # 전체 통계
    print(f"=== 실행 결과 통계 ===")
    print(f"성공한 쿼리: {successful_queries}")
    print(f"실패한 쿼리: {failed_queries}")
    print(f"성공률: {(successful_queries / len(queries) * 100):.1f}%")
    
    # 결과를 파일로 저장
    output_file = workload_file.replace('.json', '_execution_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "workload_info": {
                "benchmark_type": workload["benchmark_type"],
                "target_db": target_db,
                "total_queries": len(queries),
                "successful_queries": successful_queries,
                "failed_queries": failed_queries,
                "success_rate": successful_queries / len(queries) * 100
            },
            "execution_results": execution_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n실행 결과가 {output_file}에 저장되었습니다.")
    
    return {
        "successful_queries": successful_queries,
        "failed_queries": failed_queries,
        "success_rate": successful_queries / len(queries) * 100,
        "output_file": output_file
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("사용법: python test_sql_execution.py <워크로드_파일>")
        sys.exit(1)
    
    workload_file = sys.argv[1]
    
    if not os.path.exists(workload_file):
        print(f"워크로드 파일을 찾을 수 없습니다: {workload_file}")
        sys.exit(1)
    
    test_workload_execution(workload_file)

