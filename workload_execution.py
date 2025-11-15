#!/usr/bin/env python3
"""
PostgreSQL 워크로드 실행 테스트 스크립트
생성된 워크로드 쿼리들을 실제 PostgreSQL에서 실행하여 성공률을 측정합니다.
"""

import json
import os
import sys
import time
import re
import signal
from typing import Dict, List, Tuple
import psycopg
from psycopg import sql
import sqlite3
from decimal import Decimal
from datetime import date, datetime

# DB 연결 설정
DB_CONFIGS = {
    "cordis": {
        "type": "postgresql",
        "url": "postgresql://test:test1234@localhost:5432/cordis",
        "schema": "unics_cordis"
    },
    "oncomx": {
        "type": "postgresql",
        "url": "postgresql://test:test1234@localhost:5432/oncomx", 
        "schema": "oncomx_v1_0_25"
    },
    "sdss": {
        "type": "postgresql",
        "url": "postgresql://test:test1234@localhost:5432/sdss",
        "schema": "lite"
    },
    "eicu": {
        "type": "sqlite",
        "path": "/data/yhyunjun/HybridSQL-Benchmark/EHRSQL/EHRSQL/dataset/ehrsql/eicu/eicu.sqlite"
    },
    "mimic_iii": {
        "type": "sqlite", 
        "path": "/data/yhyunjun/HybridSQL-Benchmark/EHRSQL/EHRSQL/dataset/ehrsql/mimic_iii/mimic_iii.sqlite"
    },
    # BIRD 데이터베이스들
    "california_schools": {
        "type": "sqlite",
        "path": "/data/yhyunjun/HybridSQL-Benchmark/Bird/dev_20240627/dev_databases/california_schools/california_schools.sqlite"
    },
    "card_games": {
        "type": "sqlite",
        "path": "/data/yhyunjun/HybridSQL-Benchmark/Bird/dev_20240627/dev_databases/card_games/card_games.sqlite"
    },
    "codebase_community": {
        "type": "sqlite",
        "path": "/data/yhyunjun/HybridSQL-Benchmark/Bird/dev_20240627/dev_databases/codebase_community/codebase_community.sqlite"
    },
    "debit_card_specializing": {
        "type": "sqlite",
        "path": "/data/yhyunjun/HybridSQL-Benchmark/Bird/dev_20240627/dev_databases/debit_card_specializing/debit_card_specializing.sqlite"
    },
    "european_football_2": {
        "type": "sqlite",
        "path": "/data/yhyunjun/HybridSQL-Benchmark/Bird/dev_20240627/dev_databases/european_football_2/european_football_2.sqlite"
    },
    "financial": {
        "type": "sqlite",
        "path": "/data/yhyunjun/HybridSQL-Benchmark/Bird/dev_20240627/dev_databases/financial/financial.sqlite"
    },
    "formula_1": {
        "type": "sqlite",
        "path": "/data/yhyunjun/HybridSQL-Benchmark/Bird/dev_20240627/dev_databases/formula_1/formula_1.sqlite"
    },
    "student_club": {
        "type": "sqlite",
        "path": "/data/yhyunjun/HybridSQL-Benchmark/Bird/dev_20240627/dev_databases/student_club/student_club.sqlite"
    },
    "superhero": {
        "type": "sqlite",
        "path": "/data/yhyunjun/HybridSQL-Benchmark/Bird/dev_20240627/dev_databases/superhero/superhero.sqlite"
    },
    "thrombosis_prediction": {
        "type": "sqlite",
        "path": "/data/yhyunjun/HybridSQL-Benchmark/Bird/dev_20240627/dev_databases/thrombosis_prediction/thrombosis_prediction.sqlite"
    },
    "toxicology": {
        "type": "sqlite",
        "path": "/data/yhyunjun/HybridSQL-Benchmark/Bird/dev_20240627/dev_databases/toxicology/toxicology.sqlite"
    }
}

class TimeoutError(Exception):
    """쿼리 실행 타임아웃 예외"""
    pass

def timeout_handler(signum, frame):
    """타임아웃 시그널 핸들러"""
    raise TimeoutError("Query execution timeout")

def convert_decimal_to_float(obj):
    """Decimal, date, datetime 타입을 JSON 직렬화 가능한 타입으로 변환합니다."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, list):
        return [convert_decimal_to_float(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_decimal_to_float(item) for item in obj)
    elif isinstance(obj, dict):
        return {key: convert_decimal_to_float(value) for key, value in obj.items()}
    else:
        return obj

def execute_query_safely(conn, query: str, target_db: str, max_retries: int = 3, timeout_seconds: int = 10) -> Tuple[bool, str, float, List]:
    """
    쿼리를 안전하게 실행합니다.
    PostgreSQL과 SQLite를 모두 지원합니다.
    Args:
        conn: 데이터베이스 연결
        query: 실행할 SQL 쿼리
        target_db: 대상 데이터베이스 이름
        max_retries: 최대 재시도 횟수
        timeout_seconds: 쿼리 실행 타임아웃 (초)
    Returns: (성공여부, 에러메시지, 실행시간, 실행결과)
    """
    start_time = time.time()
    config = DB_CONFIGS[target_db]
    
    for attempt in range(max_retries):
        try:
            # 타임아웃 설정
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)
            
            try:
                if config["type"] == "postgresql":
                    # PostgreSQL: 각 쿼리를 독립적인 트랜잭션으로 실행
                    with conn.transaction():
                        with conn.cursor() as cursor:
                            cursor.execute(query)
                            # 결과를 가져와서 메모리에서 처리 (LIMIT 적용)
                            results = cursor.fetchmany(1000)  # 최대 1000개만 가져오기
                            # Decimal 타입을 float로 변환
                            results = convert_decimal_to_float(results)
                            execution_time = time.time() - start_time
                            return True, "", execution_time, results
                            
                elif config["type"] == "sqlite":
                    # SQLite: 단순 실행
                    cursor = conn.cursor()
                    cursor.execute(query)
                    # 결과를 가져와서 메모리에서 처리 (LIMIT 적용)
                    results = cursor.fetchmany(1000)  # 최대 1000개만 가져오기
                    # Decimal 타입을 float로 변환
                    results = convert_decimal_to_float(results)
                    cursor.close()
                    execution_time = time.time() - start_time
                    return True, "", execution_time, results
                    
            finally:
                # 타임아웃 해제
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
                
        except TimeoutError:
            execution_time = time.time() - start_time
            return False, f"Query timeout after {timeout_seconds} seconds", execution_time, []
        except (psycopg.Error, sqlite3.Error) as e:
            error_msg = str(e)
            # PostgreSQL 트랜잭션 오류인 경우 즉시 재시도하지 않고 다음 쿼리로 넘어감
            if "current transaction is aborted" in error_msg:
                execution_time = time.time() - start_time
                return False, error_msg, execution_time, []
            
            if attempt < max_retries - 1:
                time.sleep(0.1)  # 잠시 대기 후 재시도
                continue
            execution_time = time.time() - start_time
            return False, error_msg, execution_time, []
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            execution_time = time.time() - start_time
            return False, error_msg, execution_time, []
    
    execution_time = time.time() - start_time
    return False, "Max retries exceeded", execution_time, []

def count_masking_tokens(template: str) -> int:
    """템플릿에서 [m2_x] 형태의 고유한 토큰 개수를 카운트합니다."""
    if not template:
        return 0
    pattern = r'\[m2_\d+\]'
    tokens = re.findall(pattern, template)
    return len(set(tokens))  # 중복 제거하여 고유한 토큰 개수만 카운트

def calculate_masking_distribution(queries: List[Dict]) -> Dict[int, int]:
    """쿼리 리스트에서 NLQ 마스킹 개수 분포를 계산합니다."""
    masking_counts = {}
    
    for query in queries:
        # question_semi_template에서 마스킹 개수 계산
        question_template = query.get('question_semi_template', '')
        if isinstance(question_template, list) and question_template:
            question_template = question_template[0]
        
        masking_count = count_masking_tokens(question_template)
        masking_counts[masking_count] = masking_counts.get(masking_count, 0) + 1
    
    return masking_counts

def get_db_connection(target_db: str):
    """데이터베이스 연결을 가져옵니다."""
    if target_db not in DB_CONFIGS:
        raise ValueError(f"지원하지 않는 데이터베이스: {target_db}")
    
    config = DB_CONFIGS[target_db]
    if config["type"] == "postgresql":
        return psycopg.connect(config["url"])
    elif config["type"] == "sqlite":
        return sqlite3.connect(config["path"])
    else:
        raise ValueError(f"지원하지 않는 데이터베이스 타입: {config['type']}")


def test_workload_file(workload_file: str, target_db: str, max_queries: int = None, save_successful_only: bool = False, query_timeout: int = 10, add_execution_data: bool = False) -> Dict:
    """워크로드 파일의 쿼리들을 테스트합니다."""
    print(f"\n{'='*80}")
    print(f"🧪 워크로드 테스트: {os.path.basename(workload_file)}")
    print(f"📊 대상 DB: {target_db}")
    print(f"⏱️ 쿼리 타임아웃: {query_timeout}초")
    print(f"{'='*80}")
    
    # 워크로드 파일 로드
    if not os.path.exists(workload_file):
        print(f"❌ 워크로드 파일을 찾을 수 없습니다: {workload_file}")
        return {"error": "File not found"}
    
    with open(workload_file, 'r', encoding='utf-8') as f:
        workload_data = json.load(f)
    
    queries = workload_data.get("queries", [])
    if max_queries:
        queries = queries[:max_queries]
    
    print(f"📝 총 {len(queries)}개 쿼리 테스트 시작...")
    
    # DB 연결
    try:
        conn = get_db_connection(target_db)
        print(f"✅ DB 연결 성공: {target_db}")
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        return {"error": f"DB connection failed: {e}"}
    
    # 쿼리 실행 테스트
    results = {
        "total_queries": len(queries),
        "successful_queries": 0,
        "failed_queries": 0,
        "success_rate": 0.0,
        "total_execution_time": 0.0,
        "average_execution_time": 0.0,
        "errors": {},
        "failed_queries_details": [],
        "successful_queries_data": [],  # 성공한 쿼리 데이터 저장
        "updated_queries": []  # 실행 데이터가 추가된 쿼리들
    }
    
    start_time = time.time()
    
    for i, query_data in enumerate(queries):
        query_id = query_data.get("id", i + 1)
        sql_query = query_data.get("sql", "")
        question_semi_template = query_data.get('question_semi_template', '')
        # 쿼리 데이터 복사 (원본 보존)
        updated_query_data = query_data.copy()
        
        # literal masking 개수 계산 및 추가
        num_literal = count_masking_tokens(question_semi_template)
        updated_query_data["num_literal"] = num_literal
        
        if not sql_query:
            results["failed_queries"] += 1
            results["failed_queries_details"].append({
                "id": query_id,
                "error": "Empty SQL query"
            })
            # 실행 데이터 추가 옵션이 활성화된 경우 빈 결과라도 추가
            if add_execution_data:
                updated_query_data["execution_output"] = []
                results["updated_queries"].append(updated_query_data)
            continue
        
        # 마스킹 토큰이 남아있는지 확인
        if re.search(r'\[m[12]_\d+\]', sql_query):
            results["failed_queries"] += 1
            results["failed_queries_details"].append({
                "id": query_id,
                "error": "Unresolved masking token in SQL"
            })
            # 실행 데이터 추가 옵션이 활성화된 경우 빈 결과라도 추가
            if add_execution_data:
                updated_query_data["execution_output"] = []
                results["updated_queries"].append(updated_query_data)
            continue
        
        # 쿼리 실행
        success, error_msg, exec_time, execution_results = execute_query_safely(conn, sql_query, target_db, max_retries=3, timeout_seconds=query_timeout)
        results["total_execution_time"] += exec_time
        
        # 실행 결과를 쿼리 데이터에 추가
        if add_execution_data:
            updated_query_data["execution_output"] = execution_results
            results["updated_queries"].append(updated_query_data)
        
        if success:
            results["successful_queries"] += 1
            # 성공한 쿼리 데이터 저장
            if save_successful_only:
                results["successful_queries_data"].append(updated_query_data)
            if (i + 1) % 50 == 0:
                print(f"✅ 진행률: {i + 1}/{len(queries)} ({(i + 1)/len(queries)*100:.1f}%)")
        else:
            results["failed_queries"] += 1
            results["failed_queries_details"].append({
                "id": query_id,
                "sql": sql_query[:200] + "..." if len(sql_query) > 200 else sql_query,
                "error": error_msg
            })
            
            # 에러 타입별 카운트
            error_type = error_msg.split(':')[0] if ':' in error_msg else error_msg
            results["errors"][error_type] = results["errors"].get(error_type, 0) + 1
            
            if results["failed_queries"] <= 10:  # 처음 10개 실패만 상세 출력
                print(f"❌ 쿼리 {query_id} 실패: {error_msg[:100]}...")
    
    # 결과 계산
    total_time = time.time() - start_time
    results["success_rate"] = (results["successful_queries"] / results["total_queries"]) * 100 if results["total_queries"] > 0 else 0
    results["average_execution_time"] = results["total_execution_time"] / results["total_queries"] if results["total_queries"] > 0 else 0
    
    # 결과 출력
    print(f"\n{'='*80}")
    print(f"📊 테스트 결과 요약")
    print(f"{'='*80}")
    print(f"총 쿼리 수: {results['total_queries']}")
    print(f"성공한 쿼리: {results['successful_queries']}")
    print(f"실패한 쿼리: {results['failed_queries']}")
    print(f"성공률: {results['success_rate']:.1f}%")
    print(f"총 실행 시간: {total_time:.2f}초")
    print(f"평균 쿼리 실행 시간: {results['average_execution_time']:.3f}초")
    
    if results["errors"]:
        print(f"\n❌ 에러 타입별 통계:")
        for error_type, count in sorted(results["errors"].items(), key=lambda x: x[1], reverse=True):
            print(f"  - {error_type}: {count}회")
    
    # 상위 5개 실패 쿼리 상세 정보
    if results["failed_queries_details"]:
        print(f"\n🔍 실패한 쿼리 상세 (상위 5개):")
        for i, failed_query in enumerate(results["failed_queries_details"][:5]):
            print(f"\n  {i+1}. 쿼리 ID: {failed_query['id']}")
            if 'sql' in failed_query:
                print(f"     SQL: {failed_query['sql']}")
            print(f"     에러: {failed_query['error']}")
    
    conn.close()
    return results

def find_all_workload_files(workloads_dir: str) -> List[Tuple[str, str]]:
    """
    workloads 디렉토리에서 모든 워크로드 파일을 찾습니다.
    Returns: [(file_path, target_db), ...]
    """
    workload_files = []
    
    if not os.path.exists(workloads_dir):
        print(f"❌ 워크로드 디렉토리를 찾을 수 없습니다: {workloads_dir}")
        return workload_files
    
    # 재귀적으로 모든 .json 파일 찾기
    for root, dirs, files in os.walk(workloads_dir):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                
                # 파일 경로에서 DB 이름 추출
                target_db = None
                if "cordis" in file_path:
                    target_db = "cordis"
                elif "oncomx" in file_path:
                    target_db = "oncomx"
                elif "sdss" in file_path:
                    target_db = "sdss"
                elif "eicu" in file_path:
                    target_db = "eicu"
                elif "mimic_iii" in file_path:
                    target_db = "mimic_iii"
                # BIRD 데이터베이스들
                elif "california_schools" in file_path:
                    target_db = "california_schools"
                elif "card_games" in file_path:
                    target_db = "card_games"
                elif "codebase_community" in file_path:
                    target_db = "codebase_community"
                elif "debit_card_specializing" in file_path:
                    target_db = "debit_card_specializing"
                elif "european_football_2" in file_path:
                    target_db = "european_football_2"
                elif "financial" in file_path:
                    target_db = "financial"
                elif "formula_1" in file_path:
                    target_db = "formula_1"
                elif "student_club" in file_path:
                    target_db = "student_club"
                elif "superhero" in file_path:
                    target_db = "superhero"
                elif "thrombosis_prediction" in file_path:
                    target_db = "thrombosis_prediction"
                elif "toxicology" in file_path:
                    target_db = "toxicology"
                
                if target_db:
                    workload_files.append((file_path, target_db))
                else:
                    print(f"⚠️ 알 수 없는 DB: {file_path}")
    
    return workload_files



def save_updated_workload(original_file_path: str, target_db: str, updated_queries: List[Dict], output_dir: str):
    """실행 데이터가 추가된 쿼리들로 새로운 워크로드 파일을 생성합니다."""
    import os
    
    # 원본 파일에서 메타데이터 추출
    with open(original_file_path, 'r', encoding='utf-8') as f:
        original_data = json.load(f)
    
    # 마스킹 개수 분포 계산
    masking_distribution = calculate_masking_distribution(updated_queries)
    
    
    # 새로운 워크로드 데이터 생성
    new_workload = {
        "dataset": original_data.get("dataset", target_db),
        "nlq_masking_distribution": masking_distribution,
        "queries": updated_queries,
        "total_queries": len(updated_queries),
        "original_total_queries": original_data.get("total_queries", len(original_data.get("queries", []))),
        "updated_queries_count": len(updated_queries),
        "original_file": os.path.basename(original_file_path),
        "has_execution_data": True,
        "has_literal_count": True
    }
    
    # 원본 메타데이터 복사 (있는 경우)
    for key in ["description", "version", "created_at", "template_info"]:
        if key in original_data:
            new_workload[key] = original_data[key]
    
    # 파일명 생성 (원본과 동일하지만 _updated 접미사 추가)
    original_filename = os.path.basename(original_file_path)
    name, ext = os.path.splitext(original_filename)
    new_filename = f"{name}{ext}"
    
    # 원본 파일 경로에서 상대 경로 추출
    workloads_base = "/data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/data/workloads_v3"
    if original_file_path.startswith(workloads_base):
        relative_path = os.path.relpath(original_file_path, workloads_base)
        relative_dir = os.path.dirname(relative_path)
        
        # 출력 디렉토리 구조 생성 (원본과 동일)
        output_subdir = os.path.join(output_dir, relative_dir)
        os.makedirs(output_subdir, exist_ok=True)
        
        # 파일 저장
        output_file_path = os.path.join(output_subdir, new_filename)
    else:
        # 원본 경로가 예상과 다른 경우 DB별로 저장
        db_output_dir = os.path.join(output_dir, target_db)
        os.makedirs(db_output_dir, exist_ok=True)
        output_file_path = os.path.join(db_output_dir, new_filename)
    
    # JSON 직렬화를 위해 Decimal 타입 변환
    new_workload = convert_decimal_to_float(new_workload)
    
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(new_workload, f, indent=2, ensure_ascii=False)
    
    original_count = new_workload["original_total_queries"]
    updated_count = len(updated_queries)
    
    print(f"💾 실행 데이터 추가된 쿼리 {updated_count}/{original_count}개 저장: {output_file_path}")
    
    # 마스킹 분포 통계 출력
    if masking_distribution:
        print(f"📊 NLQ 마스킹 개수 분포:")
        total_queries = sum(masking_distribution.values())
        for masking_count in sorted(masking_distribution.keys()):
            query_count = masking_distribution[masking_count]
            percentage = (query_count / total_queries) * 100 if total_queries > 0 else 0
            print(f"   {masking_count}개 마스킹: {query_count}개 쿼리 ({percentage:.1f}%)")
    
    
    return output_file_path

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='워크로드 실행 테스트')
    parser.add_argument('--max-queries', type=int, default=None, 
                       help='파일당 최대 테스트 쿼리 수 (기본값: 전체)')
    parser.add_argument('--db-filter', type=str, nargs='+', default=None,
                       help='특정 DB만 테스트 (여러 개 가능, 예: --db-filter formula_1 student_club codebase_community)')
    parser.add_argument('--exclude-db', type=str, default=None,
                       help='제외할 DB (예: sdss)')
    parser.add_argument('--file-filter', type=str, default=None,
                       help='특정 파일 패턴만 테스트 (예: uniform_1k)')
    parser.add_argument('--save-successful', action='store_true',
                       help='성공한 쿼리들만 별도 파일로 저장')
    parser.add_argument('--output-dir', type=str, 
                       default='/data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/data/workloads_v3_not_null',
                       help='성공한 쿼리 저장 디렉토리 (기본값: workloads_v3)')
    parser.add_argument('--query-timeout', type=int, default=10,
                       help='쿼리 실행 타임아웃 (초, 기본값: 10)')
    parser.add_argument('--add-execution-data', action='store_true',
                       help='각 쿼리에 실행 결과와 literal masking 개수 추가')
    parser.add_argument('--save-updated', action='store_true',
                       help='실행 데이터가 추가된 워크로드 파일 저장')
    
    args = parser.parse_args()
    
    print("🚀 PostgreSQL 워크로드 실행 테스트 시작")
    
    # workloads 디렉토리에서 모든 파일 찾기
    workloads_dir = "/data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/data/workloads_v3"
    workload_files = find_all_workload_files(workloads_dir)
    
    if not workload_files:
        print("❌ 워크로드 파일을 찾을 수 없습니다.")
        return
    
    # 필터링 적용
    filtered_files = []
    for file_path, target_db in workload_files:
        # DB 필터 적용 (여러 개 지원)
        if args.db_filter and target_db not in args.db_filter:
            continue
        
        # DB 제외 필터 적용
        if args.exclude_db and target_db == args.exclude_db:
            continue
        
        # 파일 패턴 필터 적용
        if args.file_filter and args.file_filter not in os.path.basename(file_path):
            continue
            
        filtered_files.append((file_path, target_db))
    
    if not filtered_files:
        print("❌ 필터 조건에 맞는 워크로드 파일이 없습니다.")
        return
    
    print(f"📁 발견된 워크로드 파일: {len(workload_files)}개")
    print(f"🔍 필터링 후: {len(filtered_files)}개")
    
    for file_path, target_db in filtered_files:
        print(f"  - {os.path.basename(file_path)} ({target_db})")
    
    all_results = {}
    total_start_time = time.time()
    
    for file_path, target_db in filtered_files:
        # 워크로드 테스트 실행
        result = test_workload_file(file_path, target_db, max_queries=args.max_queries, 
                                  save_successful_only=args.save_successful, query_timeout=args.query_timeout,
                                  add_execution_data=args.add_execution_data)
        

        
        # 실행 데이터가 추가된 쿼리들 저장 (옵션이 활성화된 경우)
        if args.save_updated and "updated_queries" in result and result["updated_queries"]:
            save_updated_workload(file_path, target_db, result["updated_queries"], args.output_dir)
        
        # 결과를 파일별로 저장
        file_key = f"{target_db}_{os.path.basename(file_path)}"
        all_results[file_key] = result
    
    # 전체 결과 요약
    total_time = time.time() - total_start_time
    print(f"\n{'='*80}")
    print(f"🎯 전체 테스트 결과 요약")
    print(f"{'='*80}")
    print(f"총 테스트 시간: {total_time:.2f}초")
    print(f"테스트된 파일 수: {len(all_results)}개")
    
    # DB별 통계
    db_stats = {}
    total_queries = 0
    total_success = 0
    total_failed = 0
    
    print(f"\n📊 파일별 결과:")
    for file_key, result in all_results.items():
        if "error" in result:
            print(f"❌ {file_key}: {result['error']}")
            continue
            
        total_queries += result["total_queries"]
        total_success += result["successful_queries"] 
        total_failed += result["failed_queries"]
        
        # DB별 통계 누적
        db_name = file_key.split('_')[0]
        if db_name not in db_stats:
            db_stats[db_name] = {"total": 0, "success": 0, "failed": 0, "files": 0}
        
        db_stats[db_name]["total"] += result["total_queries"]
        db_stats[db_name]["success"] += result["successful_queries"]
        db_stats[db_name]["failed"] += result["failed_queries"]
        db_stats[db_name]["files"] += 1
        
        print(f"📄 {file_key}: {result['successful_queries']}/{result['total_queries']} 성공 ({result['success_rate']:.1f}%)")
    
    # DB별 요약
    print(f"\n📊 DB별 요약:")
    for db_name, stats in db_stats.items():
        success_rate = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"🗄️ {db_name.upper()}: {stats['success']}/{stats['total']} 성공 ({success_rate:.1f}%) - {stats['files']}개 파일")
    
    # 전체 요약
    if total_queries > 0:
        overall_success_rate = (total_success / total_queries) * 100
        print(f"\n🏆 전체 성공률: {total_success}/{total_queries} ({overall_success_rate:.1f}%)")
        print(f"📁 총 파일 수: {len(all_results)}개")
        print(f"⏱️ 평균 파일당 시간: {total_time/len(all_results):.2f}초")
    
    print(f"\n✅ 테스트 완료!")

if __name__ == "__main__":
    main()
