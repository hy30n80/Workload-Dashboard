#!/usr/bin/env python3
"""
Train 디렉토리 내의 모든 JSON 파일의 queries를 셔플하고 id를 재정렬하는 스크립트
"""
import json
import random
import os
from pathlib import Path

def shuffle_and_reindex_queries(file_path):
    """JSON 파일의 queries를 셔플하고 id를 1부터 순서대로 재할당"""
    print(f"Processing: {file_path}")
    
    # 파일 읽기
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'queries' not in data:
        print(f"  Warning: 'queries' key not found in {file_path}")
        return
    
    queries = data['queries']
    print(f"  Found {len(queries)} queries")
    
    # 셔플
    random.shuffle(queries)
    
    # id 재할당 (1부터 시작)
    for idx, query in enumerate(queries, start=1):
        query['id'] = idx
    
    # 파일 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ Shuffled and reindexed {len(queries)} queries")

def main():
    train_dir = Path("/data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/data/workloads_v16_1k/Train")
    
    # 모든 JSON 파일 찾기
    json_files = list(train_dir.rglob("*.json"))
    
    print(f"Found {len(json_files)} JSON files to process\n")
    
    # 각 파일 처리
    for json_file in sorted(json_files):
        shuffle_and_reindex_queries(json_file)
    
    print(f"\n✓ Completed processing {len(json_files)} files")

if __name__ == "__main__":
    # 시드 설정 (재현 가능하도록, 필요시 변경 가능)
    random.seed(42)
    main()

