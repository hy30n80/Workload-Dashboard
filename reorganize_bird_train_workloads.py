#!/usr/bin/env python3
"""
BIRD Train 워크로드를 domain별 distribution에 맞춰 재구성합니다.
각 DB별로 생성된 워크로드에서 domain distribution에 맞는 개수만큼 선택합니다.
"""

import json
import os
import argparse
import random
from collections import defaultdict
from typing import Dict, List, Any

# BIRD domain별 DB 매핑
BIRD_DOMAIN_DBS = {
    "University": {
        "Train": ["college_completion", "computer_student", "cs_semester", "university"],
        "Dev": ["student_club"]
    },
    "Sport": {
        "Train": ["european_football_1", "hockey", "ice_hockey_draft", "olympics", "professional_basketball", "soccer_2016"],
        "Dev": ["formula_1"]
    },
    "Software": {
        "Train": ["codebase_comments", "social_media", "software_company", "talkingdata"],
        "Dev": ["codebase_community"]
    },
    "Financial": {
        "Train": ["student_loan"],
        "Dev": ["debit_card_specializing"]
    }
}

def load_distribution(distribution_file: str, split: str, benchmark_type: str, domain: str, dist_key: str) -> Dict[str, int]:
    """domain별 distribution을 로드합니다."""
    with open(distribution_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if split not in data:
        raise ValueError(f"Split {split} not found in distribution file")
    if benchmark_type not in data[split]:
        raise ValueError(f"Benchmark {benchmark_type} not found in distribution file")
    if domain not in data[split][benchmark_type]:
        raise ValueError(f"Domain {domain} not found in distribution file")
    if dist_key not in data[split][benchmark_type][domain]:
        raise ValueError(f"Distribution key {dist_key} not found")
    
    distribution = data[split][benchmark_type][domain][dist_key]["template_distribution"]
    return distribution

def load_workload_file(workload_file: str) -> List[Dict[str, Any]]:
    """워크로드 파일을 로드합니다."""
    if not os.path.exists(workload_file):
        print(f"Warning: 워크로드 파일을 찾을 수 없습니다: {workload_file}")
        return []
    
    with open(workload_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get("queries", [])

def get_template_id_from_query(query: Dict[str, Any]) -> str:
    """쿼리에서 template_id를 추출합니다."""
    template_id = query.get("template_id")
    if template_id is None:
        return ""
    return str(template_id)


def reorganize_domain_workload(
    source_dir: str,
    output_dir: str,
    distribution_file: str,
    domain: str,
    distribution_type: str,
    criterion: str = None
) -> bool:
    """domain별 워크로드를 재구성합니다."""
    
    # distribution key 생성
    if distribution_type == "zipf":
        if criterion == "query_len":
            dist_key = f"{distribution_type}_{criterion}"
        else:
            dist_key = f"{distribution_type}_{criterion}"
    else:
        dist_key = distribution_type
    
    # zipf_random의 경우 distribution을 따르지 않고 랜덤 샘플링
    is_random_sampling = (distribution_type == "zipf" and criterion == "random")
    
    if not is_random_sampling:
        # distribution 로드
        try:
            distribution = load_distribution(distribution_file, "Train", "BIRD", domain, dist_key)
        except Exception as e:
            print(f"Error: Distribution 로드 실패 ({domain}/{dist_key}): {e}")
            return False
        
        print(f"\n{domain} domain - {dist_key} distribution:")
        print(f"  총 {len(distribution)}개의 고유 template_id")
        print(f"  총 {sum(distribution.values())}개의 샘플")
    else:
        print(f"\n{domain} domain - {dist_key} (랜덤 샘플링):")
        distribution = None  # 랜덤 샘플링이므로 distribution 없음
    
    # domain의 모든 DB에서 워크로드 수집
    domain_dbs = BIRD_DOMAIN_DBS[domain]["Train"]
    all_queries_by_db = {}
    
    for db in domain_dbs:
        # 워크로드 파일 경로 (distribution_type과 criterion에 따라 파일명이 다를 수 있음)
        if distribution_type == "zipf":
            if criterion == "query_len":
                workload_file = os.path.join(source_dir, f"Train/BIRD/{db}/zipf_query_len_1k.json")
            else:
                workload_file = os.path.join(source_dir, f"Train/BIRD/{db}/zipf_{criterion}_1k.json")
        else:
            workload_file = os.path.join(source_dir, f"Train/BIRD/{db}/uniform_rank_1k.json")
        
        queries = load_workload_file(workload_file)
        all_queries_by_db[db] = queries
        print(f"  {db}: {len(queries)}개 쿼리 로드됨")
    
    # 모든 DB의 쿼리를 합쳐서 처리
    all_queries_with_db = []  # (query, source_db) 튜플 리스트
    for db in domain_dbs:
        db_queries = all_queries_by_db[db]
        for query in db_queries:
            all_queries_with_db.append((query, db))
    
    selected_queries = []
    used_instances = set()  # domain 전체에서 중복 방지
    selected_by_db = defaultdict(int)  # DB별 선택 개수 추적
    
    if is_random_sampling:
        # zipf_random: 모든 쿼리에서 랜덤하게 1000개 선택
        random.seed(42)  # 재현성을 위한 시드 고정
        
        # 중복 없이 랜덤 샘플링
        available_queries = []
        for query, source_db in all_queries_with_db:
            query_id = query.get("id")
            if query_id is None:
                continue
            
            template_id = get_template_id_from_query(query)
            full_template_id = f"{source_db}_{template_id}"
            instance_key = (full_template_id, query_id)
            
            if instance_key not in used_instances:
                available_queries.append((query, source_db))
                used_instances.add(instance_key)
        
        # 1000개 랜덤 샘플링
        target_count = 1000
        if len(available_queries) < target_count:
            print(f"  Warning: 사용 가능한 쿼리({len(available_queries)})가 목표 개수({target_count})보다 적습니다.")
            target_count = len(available_queries)
        
        sampled = random.sample(available_queries, target_count)
        for query, source_db in sampled:
            # target_db 정보를 query에 추가
            query["target_db"] = source_db
            selected_queries.append(query)
            selected_by_db[source_db] += 1
        
        print(f"  총 {len(available_queries)}개 중 {target_count}개 랜덤 샘플링")
    else:
        # distribution에 맞춰 쿼리 선택
        # template_id별로 쿼리 그룹화
        queries_by_template = defaultdict(list)
        for query, source_db in all_queries_with_db:
            template_id = get_template_id_from_query(query)
            # 각 DB별로 full_template_id 생성하여 확인
            full_template_id = f"{source_db}_{template_id}"
            if full_template_id in distribution:
                queries_by_template[full_template_id].append((query, source_db))
        
        # distribution에 따라 쿼리 선택
        for template_id, count in distribution.items():
            if template_id not in queries_by_template:
                print(f"  Warning: template_id {template_id}에 해당하는 쿼리를 찾을 수 없습니다.")
                continue
            
            available_queries_with_db = queries_by_template[template_id]
            selected_count = 0
            
            for query, source_db in available_queries_with_db:
                if selected_count >= count:
                    break
                
                # instance 중복 체크 (workload 파일의 id를 기준으로 고유 instance 판단)
                query_id = query.get("id")
                if query_id is None:
                    print(f"  Warning: query에 id가 없습니다. 건너뜁니다.")
                    continue
                
                instance_key = (template_id, query_id)
                
                if instance_key in used_instances:
                    continue
                used_instances.add(instance_key)
                
                # target_db 정보를 query에 추가
                query["target_db"] = source_db
                selected_queries.append(query)
                selected_by_db[source_db] += 1
                selected_count += 1
            
            if selected_count < count:
                print(f"  Warning: template_id {template_id}에서 요청한 {count}개 중 {selected_count}개만 선택되었습니다.")
    
    # DB별 선택 개수 출력
    for db in domain_dbs:
        print(f"  {db}: {selected_by_db[db]}개 쿼리 선택됨")
    
    # 총 개수 확인
    total_selected = len(selected_queries)
    if is_random_sampling:
        target_count = 1000
        # 선택된 쿼리들의 template_id 분포 계산
        template_distribution = defaultdict(int)
        for query in selected_queries:
            template_id = get_template_id_from_query(query)
            target_db = query.get("target_db")
            
            if target_db:
                full_template_id = f"{target_db}_{template_id}"
                template_distribution[full_template_id] += 1
            else:
                print(f"  Warning: query에 target_db 정보가 없습니다. template_id: {template_id}")
        
        # 내림차순으로 정렬
        sorted_distribution = dict(sorted(template_distribution.items(), key=lambda x: x[1], reverse=True))
        
        # initial_distribution.json에 저장
        if os.path.exists(distribution_file):
            with open(distribution_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
        else:
            all_data = {}
        
        # 계층 구조 생성/업데이트: split -> benchmark_type -> target_db -> distribution_type_criterion
        if "Train" not in all_data:
            all_data["Train"] = {}
        if "BIRD" not in all_data["Train"]:
            all_data["Train"]["BIRD"] = {}
        if domain not in all_data["Train"]["BIRD"]:
            all_data["Train"]["BIRD"][domain] = {}
        
        # template_distribution 저장
        all_data["Train"]["BIRD"][domain][dist_key] = {
            "config": {
                "distribution_type": distribution_type,
                "criterion": criterion if distribution_type == "zipf" else None,
                "alpha": None,
                "power_law_s": None,
                "num_samples": total_selected,
                "seed": 42
            },
            "statistics": {
                "total_samples": total_selected,
                "unique_templates": len(sorted_distribution),
            },
            "template_distribution": sorted_distribution
        }
        
        # JSON 파일에 저장
        with open(distribution_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ Distribution 저장 완료: {distribution_file}")
        print(f"    경로: Train -> BIRD -> {domain} -> {dist_key}")
        print(f"    총 {len(sorted_distribution)}개의 고유 template_id")
    else:
        target_count = sum(distribution.values())
    
    print(f"\n  선택된 총 쿼리 수: {total_selected} / 목표: {target_count}")
    
    # 1000개를 못 채웠을 때 추가 샘플링
    if total_selected < target_count:
        print(f"  ⚠️  목표 개수({target_count})를 채우지 못했습니다. ({total_selected}개만 선택됨)")
        print(f"  추가 샘플링 시작...")
        
        if not is_random_sampling and distribution:
            # distribution의 내림차순 순서대로 하나씩 추가 샘플링
            sorted_distribution = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
            
            # template_id별로 쿼리 그룹화 (이미 사용된 instance 제외)
            queries_by_template = defaultdict(list)
            for query, source_db in all_queries_with_db:
                template_id = get_template_id_from_query(query)
                full_template_id = f"{source_db}_{template_id}"
                if full_template_id in distribution:
                    queries_by_template[full_template_id].append((query, source_db))
            
            # 내림차순 순서대로 하나씩 추가 샘플링
            # 각 template_id에서 하나씩만 가져오고, 1000개가 안 되면 다시 처음부터 순회
            additional_count = 0
            round_count = 0
            
            while total_selected < target_count:
                round_count += 1
                round_added = 0
                
                # 내림차순 순서대로 각 template_id에서 하나씩만 가져오기
                for template_id, _ in sorted_distribution:
                    if total_selected >= target_count:
                        break
                    
                    if template_id not in queries_by_template:
                        continue
                    
                    available_queries_with_db = queries_by_template[template_id]
                    
                    # 이 template_id에서 사용 가능한 쿼리 중 하나만 찾기
                    found = False
                    for query, source_db in available_queries_with_db:
                        if found:
                            break
                        
                        query_id = query.get("id")
                        if query_id is None:
                            continue
                        
                        instance_key = (template_id, query_id)
                        
                        if instance_key in used_instances:
                            continue
                        
                        # 중복되지 않은 쿼리 발견
                        used_instances.add(instance_key)
                        query["target_db"] = source_db
                        selected_queries.append(query)
                        selected_by_db[source_db] += 1
                        total_selected += 1
                        additional_count += 1
                        round_added += 1
                        found = True
                
                # 이번 라운드에서 추가된 쿼리가 없으면 더 이상 사용 가능한 쿼리가 없음
                if round_added == 0:
                    break
            
            if additional_count > 0:
                print(f"  ✅ 추가로 {additional_count}개 샘플링하여 총 {total_selected}개가 되었습니다.")
            else:
                print(f"  ⚠️  추가 샘플링을 시도했지만 더 이상 사용 가능한 쿼리가 없습니다.")
        
        if total_selected < target_count:
            print(f"  ⚠️  최종적으로 목표 개수({target_count})를 채우지 못했습니다. ({total_selected}개만 선택됨)")
    
    # 최종 개수 재계산
    total_selected = len(selected_queries)
    
    # 출력 디렉토리 생성
    output_path = os.path.join(output_dir, f"Train/BIRD/{domain}")
    os.makedirs(output_path, exist_ok=True)
    
    # 출력 파일명 생성
    if distribution_type == "zipf":
        if criterion == "query_len":
            output_filename = f"zipf_{criterion}_1k.json"
        else:
            output_filename = f"zipf_{criterion}_1k.json"
    else:
        output_filename = "uniform_rank_1k.json"
    
    output_file = os.path.join(output_path, output_filename)
    
    # 쿼리 ID 재할당 및 target_db 확인
    for idx, query in enumerate(selected_queries, 1):
        query["id"] = idx
        # source_db가 있으면 제거하고 target_db로 통일
        if "source_db" in query:
            if "target_db" not in query:
                query["target_db"] = query["source_db"]
            del query["source_db"]
        elif "target_db" not in query:
            # target_db가 없으면 domain의 첫 번째 DB를 기본값으로 사용
            query["target_db"] = domain_dbs[0] if domain_dbs else domain
    
    # DB별 샘플링 개수를 딕셔너리로 변환
    queries_per_db = dict(selected_by_db)
    
    # 결과 저장
    result = {
        "config": {
            "benchmark_type": "BIRD",
            "split": "Train",
            "domain": domain,
            "distribution_type": distribution_type,
            "criterion": criterion if distribution_type == "zipf" else None,
            "num_queries": total_selected,
            "target_count": target_count
        },
        "statistics": {
            "total_queries": total_selected,
            "target_count": target_count,
            "is_complete": total_selected >= target_count,
            "queries_per_db": queries_per_db
        },
        "queries": selected_queries
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"  ✅ 저장 완료: {output_file}")
    
    return total_selected >= target_count

def main():
    parser = argparse.ArgumentParser(description='BIRD Train 워크로드를 domain별로 재구성합니다.')
    
    parser.add_argument('--source_dir', type=str, default='data/workloads_v15_1k',
                       help='원본 워크로드 디렉토리 (기본값: data/workloads_v15_1k)')
    
    parser.add_argument('--output_dir', type=str, default='data/workloads_v16_1k',
                       help='출력 디렉토리 (기본값: data/workloads_v16_1k)')
    
    parser.add_argument('--distribution_file', type=str, default='tools/distribution/initial_distribution.json',
                       help='Distribution 파일 경로 (기본값: tools/distribution/initial_distribution.json)')
    
    args = parser.parse_args()
    
    # 모든 domain과 distribution 타입 조합 처리
    domains = ["University", "Sport", "Software", "Financial"]
    distribution_configs = [
        ("uniform", None),
        ("zipf", "random"),
        ("zipf", "query_len")
    ]
    
    print("=" * 60)
    print("BIRD Train 워크로드 재구성 시작")
    print("=" * 60)
    
    incomplete_count = 0
    
    for domain in domains:
        for distribution_type, criterion in distribution_configs:
            print(f"\n{'=' * 60}")
            print(f"처리 중: {domain} - {distribution_type}" + (f"({criterion})" if criterion else ""))
            print(f"{'=' * 60}")
            
            is_complete = reorganize_domain_workload(
                args.source_dir,
                args.output_dir,
                args.distribution_file,
                domain,
                distribution_type,
                criterion
            )
            
            if not is_complete:
                incomplete_count += 1
    
    print(f"\n{'=' * 60}")
    print("재구성 완료!")
    print(f"{'=' * 60}")
    print(f"출력 디렉토리: {args.output_dir}")
    if incomplete_count > 0:
        print(f"⚠️  {incomplete_count}개의 조합에서 목표 개수를 채우지 못했습니다.")
    else:
        print("✅ 모든 조합에서 목표 개수를 채웠습니다.")

if __name__ == "__main__":
    main()

