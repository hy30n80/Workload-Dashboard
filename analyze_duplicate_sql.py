import json
from pathlib import Path
from collections import Counter

def load_uniform_1k_json(file_path):
    """uniform_rank_1k.json 파일을 로드하고 queries와 statistics를 반환합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('queries', []), data.get('statistics', {})
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None, None

def count_duplicate_sql_queries(queries):
    """queries에서 정확히 똑같은 SQL 쿼리의 중복 개수를 체크합니다.
    
    Args:
        queries: 쿼리 리스트
        
    Returns:
        tuple: (전체 쿼리 개수, 고유 쿼리 개수, 중복 쿼리 개수, 중복 쿼리 상세 정보)
    """
    if not queries:
        return 0, 0, 0, {}
    
    # SQL 쿼리 문자열 추출
    sql_queries = []
    for query in queries:
        sql = query.get('sql', '')
        if sql:  # SQL이 있는 경우만 추가
            sql_queries.append(sql)
    
    total_count = len(sql_queries)
    
    # SQL 쿼리별 개수 집계
    sql_counter = Counter(sql_queries)
    
    # 중복 쿼리 찾기 (2개 이상인 것들)
    duplicate_queries = {sql: count for sql, count in sql_counter.items() if count > 1}
    
    unique_count = len(sql_counter)
    duplicate_count = total_count - unique_count  # 중복된 쿼리의 총 개수
    
    return total_count, unique_count, duplicate_count, duplicate_queries

def main(): 
    base_dir = Path("/data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/data/workloads_v15_1k/Dev")
    
    datasets = ["BIRD", "EHRSQL", "ScienceBenchmark"]
    
    # 전체 통계
    total_stats = {
        'total_workloads': 0,
        'total_queries': 0,
        'total_unique_queries': 0,
        'total_duplicate_queries': 0,
        'workloads_with_duplicates': 0
    }
    
    print("=" * 80)
    print("SQL Query 중복 체크 리포트")
    print("=" * 80)
    
    for dataset in datasets:
        dataset_path = base_dir / dataset
        if not dataset_path.exists():
            print(f"\n⚠️  Warning: {dataset_path} does not exist. Skipping...")
            continue
        
        print(f"\n🔹 Processing {dataset}...")
        print("-" * 80)
        
        dataset_total = 0
        dataset_unique = 0
        dataset_duplicate = 0
        dataset_workloads_with_dups = 0
        
        # 각 DB 디렉토리 탐색
        for db_dir in sorted(dataset_path.iterdir()):
            if not db_dir.is_dir():
                continue
            
            db_name = db_dir.name
            uniform_file = db_dir / "uniform_rank_1k.json"
            
            if not uniform_file.exists():
                print(f"  ⚠️  {db_name}: uniform_rank_1k.json not found. Skipping...")
                continue
            
            # JSON 파일 로드
            queries, stats = load_uniform_1k_json(uniform_file)
            if queries is None:
                continue
            
            # 중복 쿼리 체크
            total_count, unique_count, duplicate_count, duplicate_queries = count_duplicate_sql_queries(queries)
            
            dataset_total += total_count
            dataset_unique += unique_count
            dataset_duplicate += duplicate_count
            
            total_stats['total_workloads'] += 1
            total_stats['total_queries'] += total_count
            total_stats['total_unique_queries'] += unique_count
            total_stats['total_duplicate_queries'] += duplicate_count
            
            # 결과 출력
            if duplicate_count > 0:
                dataset_workloads_with_dups += 1
                total_stats['workloads_with_duplicates'] += 1
                print(f"  🔴 {db_name}:")
                print(f"     전체 쿼리: {total_count}, 고유 쿼리: {unique_count}, 중복 쿼리: {duplicate_count}")
                print(f"     중복 비율: {duplicate_count/total_count*100:.2f}%")
                
                # 가장 많이 중복된 쿼리 상위 5개 출력
                if duplicate_queries:
                    sorted_dups = sorted(duplicate_queries.items(), key=lambda x: x[1], reverse=True)
                    print(f"     중복 쿼리 상위 5개:")
                    for idx, (sql, count) in enumerate(sorted_dups[:5], 1):
                        sql_preview = sql[:80] + "..." if len(sql) > 80 else sql
                        print(f"       {idx}. (중복 {count}회) {sql_preview}")
            else:
                print(f"  ✅ {db_name}: 중복 없음 (전체: {total_count}, 고유: {unique_count})")
        
        # 데이터셋별 요약
        print(f"\n📊 {dataset} 요약:")
        print(f"   전체 쿼리: {dataset_total}, 고유 쿼리: {dataset_unique}, 중복 쿼리: {dataset_duplicate}")
        if dataset_total > 0:
            print(f"   중복 비율: {dataset_duplicate/dataset_total*100:.2f}%")
        print(f"   중복이 있는 워크로드: {dataset_workloads_with_dups}")
    
    # 전체 요약
    print("\n" + "=" * 80)
    print("전체 요약")
    print("=" * 80)
    print(f"전체 워크로드 수: {total_stats['total_workloads']}")
    print(f"전체 쿼리 수: {total_stats['total_queries']}")
    print(f"전체 고유 쿼리 수: {total_stats['total_unique_queries']}")
    print(f"전체 중복 쿼리 수: {total_stats['total_duplicate_queries']}")
    if total_stats['total_queries'] > 0:
        print(f"전체 중복 비율: {total_stats['total_duplicate_queries']/total_stats['total_queries']*100:.2f}%")
    print(f"중복이 있는 워크로드 수: {total_stats['workloads_with_duplicates']}")
    if total_stats['total_workloads'] > 0:
        print(f"중복 워크로드 비율: {total_stats['workloads_with_duplicates']/total_stats['total_workloads']*100:.2f}%")
    print("=" * 80)

if __name__ == "__main__":
    main()

