#!/usr/bin/env python3
"""
최종 워크로드에서 template 분포를 계산하여 generated_distribution.json을 생성합니다.
"""

import json
import os
import argparse
from collections import defaultdict
from typing import Dict, Any

def load_workload_file(workload_file: str) -> Dict[str, Any]:
    """워크로드 파일을 로드합니다."""
    if not os.path.exists(workload_file):
        print(f"Warning: 워크로드 파일을 찾을 수 없습니다: {workload_file}")
        return None
    
    with open(workload_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data

def get_template_id_from_query(query: Dict[str, Any]) -> str:
    """쿼리에서 template_id를 추출합니다."""
    template_id = query.get("template_id")
    if template_id is None:
        return None
    return str(template_id)

def calculate_template_distribution(workload_data: Dict[str, Any], benchmark_type: str, split: str, target_db: str) -> Dict[str, int]:
    """워크로드에서 template 분포를 계산합니다."""
    queries = workload_data.get("queries", [])
    template_counts = defaultdict(int)
    
    for query in queries:
        template_id = get_template_id_from_query(query)
        if template_id is None:
            continue
        
        # BIRD Train의 경우 target_db와 template_id를 조합
        if benchmark_type == "BIRD" and split == "Train":
            target_db_from_query = query.get("target_db")
            if target_db_from_query:
                full_template_id = f"{target_db_from_query}_{template_id}"
            else:
                # target_db가 없으면 domain 이름만 사용 (하지만 이 경우는 없어야 함)
                full_template_id = f"{target_db}_{template_id}"
        else:
            # EHRSQL, ScienceBenchmark의 경우 template_id만 사용
            full_template_id = template_id
        
        template_counts[full_template_id] += 1
    
    # 내림차순으로 정렬
    sorted_distribution = dict(sorted(template_counts.items(), key=lambda x: x[1], reverse=True))
    
    return sorted_distribution

def process_workload_directory(workload_dir: str, output_file: str):
    """워크로드 디렉토리를 순회하며 template 분포를 계산합니다."""
    
    all_data = {}
    
    # Dev와 Train 처리
    for split in ["Dev", "Train"]:
        split_dir = os.path.join(workload_dir, split)
        if not os.path.exists(split_dir):
            continue
        
        all_data[split] = {}
        
        # EHRSQL 처리
        ehrsql_dir = os.path.join(split_dir, "EHRSQL")
        if os.path.exists(ehrsql_dir):
            all_data[split]["EHRSQL"] = {}
            for db in ["eicu", "mimic_iii"]:
                db_dir = os.path.join(ehrsql_dir, db)
                if os.path.exists(db_dir):
                    all_data[split]["EHRSQL"][db] = {}
                    
                    # 각 distribution 타입 처리
                    for dist_file in os.listdir(db_dir):
                        if not dist_file.endswith("_1k.json"):
                            continue
                        
                        # 파일명에서 distribution_type과 criterion 추출
                        base_name = dist_file.replace("_1k.json", "")
                        if base_name == "uniform_rank":
                            distribution_type = "uniform"
                            criterion = None
                            dist_key = "uniform"
                        elif base_name.startswith("zipf_"):
                            parts = base_name.split("_")
                            distribution_type = "zipf"
                            if len(parts) > 1:
                                criterion = parts[1]  # random 또는 query_len
                                dist_key = f"zipf_{criterion}"
                            else:
                                criterion = None
                                dist_key = "zipf"
                        else:
                            continue
                        
                        workload_file = os.path.join(db_dir, dist_file)
                        workload_data = load_workload_file(workload_file)
                        
                        if workload_data:
                            template_distribution = calculate_template_distribution(
                                workload_data, "EHRSQL", split, db
                            )
                            
                            all_data[split]["EHRSQL"][db][dist_key] = {
                                "config": {
                                    "distribution_type": distribution_type,
                                    "criterion": criterion,
                                    "alpha": None,
                                    "power_law_s": None,
                                    "num_samples": len(workload_data.get("queries", [])),
                                    "seed": 42
                                },
                                "statistics": {
                                    "total_samples": len(workload_data.get("queries", [])),
                                    "unique_templates": len(template_distribution),
                                },
                                "template_distribution": template_distribution
                            }
                            
                            print(f"✅ {split}/EHRSQL/{db}/{dist_key}: {len(template_distribution)}개 고유 template, {len(workload_data.get('queries', []))}개 쿼리")
        
        # ScienceBenchmark 처리
        science_dir = os.path.join(split_dir, "ScienceBenchmark")
        if os.path.exists(science_dir):
            all_data[split]["ScienceBenchmark"] = {}
            for db in ["cordis", "oncomx", "sdss"]:
                db_dir = os.path.join(science_dir, db)
                if os.path.exists(db_dir):
                    all_data[split]["ScienceBenchmark"][db] = {}
                    
                    # 각 distribution 타입 처리
                    for dist_file in os.listdir(db_dir):
                        if not dist_file.endswith("_1k.json"):
                            continue
                        
                        # 파일명에서 distribution_type과 criterion 추출
                        base_name = dist_file.replace("_1k.json", "")
                        if base_name == "uniform_rank":
                            distribution_type = "uniform"
                            criterion = None
                            dist_key = "uniform"
                        elif base_name.startswith("zipf_"):
                            parts = base_name.split("_")
                            distribution_type = "zipf"
                            if len(parts) > 1:
                                criterion = parts[1]  # random 또는 query_len
                                dist_key = f"zipf_{criterion}"
                            else:
                                criterion = None
                                dist_key = "zipf"
                        else:
                            continue
                        
                        workload_file = os.path.join(db_dir, dist_file)
                        workload_data = load_workload_file(workload_file)
                        
                        if workload_data:
                            template_distribution = calculate_template_distribution(
                                workload_data, "ScienceBenchmark", split, db
                            )
                            
                            all_data[split]["ScienceBenchmark"][db][dist_key] = {
                                "config": {
                                    "distribution_type": distribution_type,
                                    "criterion": criterion,
                                    "alpha": None,
                                    "power_law_s": None,
                                    "num_samples": len(workload_data.get("queries", [])),
                                    "seed": 42
                                },
                                "statistics": {
                                    "total_samples": len(workload_data.get("queries", [])),
                                    "unique_templates": len(template_distribution),
                                },
                                "template_distribution": template_distribution
                            }
                            
                            print(f"✅ {split}/ScienceBenchmark/{db}/{dist_key}: {len(template_distribution)}개 고유 template, {len(workload_data.get('queries', []))}개 쿼리")

        # BIRD 처리
        bird_dir = os.path.join(split_dir, "BIRD")
        if os.path.exists(bird_dir):
            all_data[split]["BIRD"] = {}
            
            # Dev의 경우 개별 DB, Train의 경우 domain
            if split == "Dev":
                bird_dbs = ["University", "Sport", "Software", "Financial"]
            else:
                bird_dbs = ["University", "Sport", "Software", "Financial"]
            
            for db_or_domain in bird_dbs:
                db_dir = os.path.join(bird_dir, db_or_domain)
                if os.path.exists(db_dir):
                    all_data[split]["BIRD"][db_or_domain] = {}
                    
                    # 각 distribution 타입 처리
                    for dist_file in os.listdir(db_dir):
                        if not dist_file.endswith("_1k.json"):
                            continue
                        
                        # 파일명에서 distribution_type과 criterion 추출
                        base_name = dist_file.replace("_1k.json", "")
                        if base_name == "uniform_rank":
                            distribution_type = "uniform"
                            criterion = None
                            dist_key = "uniform"
                        elif base_name.startswith("zipf_"):
                            parts = base_name.split("_")
                            distribution_type = "zipf"
                            if len(parts) > 1:
                                criterion = parts[1]  # random 또는 query_len
                                dist_key = f"zipf_{criterion}"
                            else:
                                criterion = None
                                dist_key = "zipf"
                        else:
                            continue
                        
                        workload_file = os.path.join(db_dir, dist_file)
                        workload_data = load_workload_file(workload_file)
                        
                        if workload_data:
                            template_distribution = calculate_template_distribution(
                                workload_data, "BIRD", split, db_or_domain
                            )
                            
                            all_data[split]["BIRD"][db_or_domain][dist_key] = {
                                "config": {
                                    "distribution_type": distribution_type,
                                    "criterion": criterion,
                                    "alpha": None,
                                    "power_law_s": None,
                                    "num_samples": len(workload_data.get("queries", [])),
                                    "seed": 42
                                },
                                "statistics": {
                                    "total_samples": len(workload_data.get("queries", [])),
                                    "unique_templates": len(template_distribution),
                                },
                                "template_distribution": template_distribution
                            }
                            
                            print(f"✅ {split}/BIRD/{db_or_domain}/{dist_key}: {len(template_distribution)}개 고유 template, {len(workload_data.get('queries', []))}개 쿼리")
    
    # JSON 파일에 저장
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Generated distribution이 {output_file}에 저장되었습니다.")

def main():
    parser = argparse.ArgumentParser(description='최종 워크로드에서 template 분포를 계산하여 generated_distribution.json을 생성합니다.')
    parser.add_argument('--version', type=str, default='v10')
    parser.add_argument('--workload_dir', type=str, default='data/workloads_v16_1k',
                       help='워크로드 디렉토리 (기본값: data/workloads_v16_1k)')
    
    parser.add_argument('--output_file', type=str, default=f'tools/distribution/generated_distribution.json',
                       help='출력 파일 경로 (기본값: tools/distribution/generated_distribution.json)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Generated Distribution 생성 시작")
    print("=" * 60)
    print(f"워크로드 디렉토리: {args.workload_dir}")
    print(f"출력 파일: {args.output_file}")
    print("=" * 60)
    
    process_workload_directory(args.workload_dir, args.output_file)
    
    print("\n" + "=" * 60)
    print("Generated Distribution 생성 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()

