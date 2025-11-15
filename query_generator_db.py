import json
import argparse
import numpy as np
import random
import os
import re
import sqlite3
from typing import Optional, Dict, Any, List
from sqlglot import parse_one, expressions as exp
from decimal import Decimal
from datetime import date, datetime
import pdb as pdb



def load_distribution_data(distribution_file, benchmark_type, split, target_db):
    """분포 데이터를 로드합니다."""
    if not os.path.exists(distribution_file):
        raise FileNotFoundError(f"분포 파일을 찾을 수 없습니다: {distribution_file}")
    
    with open(distribution_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 해당 split과 target_db의 데이터 추출
    if benchmark_type == "EHRSQL":
        if split not in data["EHRSQL"]:
            raise ValueError(f"지원하지 않는 split: {split}")
        if target_db not in data["EHRSQL"][split]:
            raise ValueError(f"지원하지 않는 target_db: {target_db}")
        
        templates = data["EHRSQL"][split][target_db]["templates"]
    elif benchmark_type == "ScienceBenchmark":
        if split not in data["ScienceBenchmark"]:
            raise ValueError(f"지원하지 않는 split: {split}")
        if target_db not in data["ScienceBenchmark"][split]:
            raise ValueError(f"지원하지 않는 target_db: {target_db}")
        
        templates = data["ScienceBenchmark"][split][target_db]["templates"]

    
    elif benchmark_type == "BIRD":
        # pdb.set_trace()
        if split not in data["BIRD"]:
            raise ValueError(f"지원하지 않는 split: {split}")
        if target_db not in data["BIRD"][split]:
            raise ValueError(f"지원하지 않는 target_db: {target_db}")
        
        templates = data["BIRD"][split][target_db]["templates"]
        print(f"BIRD {target_db}: {len(templates)}개 템플릿 로드됨")
    
    return templates

def load_combined_distribution_data(distribution_file, benchmark_type, target_db):
    """Train과 Dev의 모든 템플릿을 합쳐서 로드합니다."""
    if not os.path.exists(distribution_file):
        raise FileNotFoundError(f"분포 파일을 찾을 수 없습니다: {distribution_file}")
    
    with open(distribution_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    combined_templates = []
    
    # Train과 Dev split의 템플릿을 모두 합침
    for split in ["Train", "Dev"]:
        if benchmark_type == "EHRSQL":
            if split in data["EHRSQL"] and target_db in data["EHRSQL"][split]:
                split_templates = data["EHRSQL"][split][target_db]["templates"]
                # 템플릿에 split 정보 추가
                for template in split_templates:
                    template_copy = template.copy()
                    template_copy["source_split"] = split
                    combined_templates.append(template_copy)
        elif benchmark_type == "ScienceBenchmark":
            if split in data["ScienceBenchmark"] and target_db in data["ScienceBenchmark"][split]:
                split_templates = data["ScienceBenchmark"][split][target_db]["templates"]
                # 템플릿에 split 정보 추가
                for template in split_templates:
                    template_copy = template.copy()
                    template_copy["source_split"] = split
                    combined_templates.append(template_copy)
        elif benchmark_type == "BIRD":
            if split in data["BIRD"] and target_db in data["BIRD"][split]:
                split_templates = data["BIRD"][split][target_db]["templates"]
                # 템플릿에 split 정보 추가
                for template in split_templates:
                    template_copy = template.copy()
                    template_copy["source_split"] = split
                    combined_templates.append(template_copy)
    
    print(f"Combined templates: {len(combined_templates)} (Train + Dev)")
    return combined_templates




def sample_templates_zipf(templates, num_samples, criterion="rank", alpha=1.0, power_law_s=2.0):
    """Zipf 분포 또는 Power law 분포에 따라 템플릿을 샘플링합니다."""
    n = len(templates)
    
    def get_question_length(template):
        question_template = template['question_semi_template']
        if isinstance(question_template, list):
            return len(question_template[0]) if question_template else 0
        else:
            return len(question_template)
    
    # criterion에 따라 템플릿을 재정렬
    if criterion == "random":
        # template_id를 무작위로 섞어서 rank 매김
        shuffled_templates = templates.copy()
        random.shuffle(shuffled_templates)
        sorted_templates = shuffled_templates
    elif criterion == "rank":
        # cnt 기준으로 정렬 (이미 정렬되어 있음)
        sorted_templates = templates
    elif criterion == "query_len":
        # question_semi_template 길이 기준으로 정렬 (긴 질문이 높은 rank)
        sorted_templates = sorted(templates, key=get_question_length, reverse=False)
    else:
        raise ValueError(f"지원하지 않는 criterion: {criterion}")
    
    if criterion == "query_len":
        # Power law 분포: p(k) = C * k^(-s)
        # k는 question_semi_template 길이, s는 power law 지수
        def get_question_length_for_power_law(template):
            question_template = template['question_semi_template']
            if isinstance(question_template, list):
                return len(question_template[0]) if question_template else 0
            else:
                return len(question_template)
        
        question_semi_template_lengths = [get_question_length_for_power_law(template) for template in sorted_templates]
        
        # Power law 확률 계산: p(k) = k^(-s)
        unnormalized_probs = np.array([length ** (-power_law_s) for length in question_semi_template_lengths])
        
        # 확률 정규화
        normalized_probs = unnormalized_probs / np.sum(unnormalized_probs)
        
        # 템플릿 인덱스 샘플링
        sampled_indices = np.random.choice(n, size=num_samples, p=normalized_probs, replace=True)
        
    else:
        # Zipf 분포 확률 계산
        ranks = np.arange(1, n + 1)
        unnormalized_probs = 1 / (ranks ** alpha)
        
        # 확률 정규화
        normalized_probs = unnormalized_probs / np.sum(unnormalized_probs)
        
        # 템플릿 인덱스 샘플링 (rank-1을 인덱스로 변환)
        sampled_ranks = np.random.choice(ranks, size=num_samples, p=normalized_probs, replace=True)
        sampled_indices = sampled_ranks - 1  # rank를 0-based 인덱스로 변환
    
    # 샘플링된 템플릿들 반환
    sampled_templates = [sorted_templates[i] for i in sampled_indices]
    
    return sampled_templates

def sample_templates_uniform(templates, num_samples):
    """균등 분포에 따라 템플릿을 샘플링합니다."""
    sampled_templates = random.choices(templates, k=num_samples)
    return sampled_templates

def save_template_distribution(sampled_templates, output_file):
    """샘플링된 템플릿 분포를 파일로 저장합니다."""
    # 템플릿 분포 계산
    template_counts = {}
    for template in sampled_templates:
        template_id = template["template_id"]
        template_counts[template_id] = template_counts.get(template_id, 0) + 1
    
    # 분포 정보 생성
    distribution_info = {
        "total_templates": len(sampled_templates),
        "unique_templates": len(template_counts),
        "template_distribution": dict(sorted(template_counts.items(), key=lambda x: x[1], reverse=True)),
        "top_20_distribution": dict(sorted(template_counts.items(), key=lambda x: x[1], reverse=True)[:20])
    }
    
    # 분포 파일명 생성
    base_name = os.path.splitext(output_file)[0]
    distribution_file = f"{base_name}_template_distribution.json"
    
    # 파일 저장
    with open(distribution_file, 'w', encoding='utf-8') as f:
        json.dump(distribution_info, f, indent=2, ensure_ascii=False)
    
    print(f"템플릿 분포가 {distribution_file}에 저장되었습니다.")
    return distribution_file





def update_existing_json_with_original_masking_stats(output_file, benchmark_type, split, target_db, 
                                                   distribution_type, num_queries, distribution_file,
                                                   criterion="rank", alpha=1.0, power_law_s=2.0):
    """기존 JSON 파일에 original_templates_per_masking_cnt 필드만 추가합니다."""
    
    # 1) 기존 결과 파일 로드
    if not os.path.exists(output_file):
        print(f"Error: {output_file} 파일이 존재하지 않습니다.")
        return

    with open(output_file, 'r', encoding='utf-8') as f:
        result_data = json.load(f)
    
    # 기존 파일에 이미 해당 필드가 있는지 확인
    if 'statistics' in result_data and 'original_templates_per_masking_cnt' in result_data['statistics']:
        print(f"Warning: {output_file}에 이미 'original_templates_per_masking_cnt' 필드가 있습니다.")
        print("기존 값을 덮어씁니다.")

    # 2) 분포 데이터 로드 (원 실행과 동일하게)
    if split == "Combined":
        templates = load_combined_distribution_data(distribution_file, benchmark_type, target_db)
    else:
        templates = load_distribution_data(distribution_file, benchmark_type, split, target_db)

    # 3) 동일 분포로 샘플링
    if distribution_type == "zipf":
        sampled_templates = sample_templates_zipf(templates, num_queries, criterion, alpha, power_law_s)
    else:
        sampled_templates = sample_templates_uniform(templates, num_queries)

    # 4) original_templates_per_masking_cnt 계산
    templates_per_masking_cnt = {}
    for template in sampled_templates:
        masking_cnt = 0 
        mask_type = "m2"
        for idx in range(len(template["literals"])):
            mask_pattern = f"[{mask_type}_{idx}]"
            if mask_pattern in template["question_semi_template"][0]:
                masking_cnt += 1    
        templates_per_masking_cnt[masking_cnt] = templates_per_masking_cnt.get(masking_cnt, 0) + 1

    # 5) 기존 결과에 필드만 주입
    stats = result_data.setdefault('statistics', {})
    # 기존 키는 절대 건드리지 않고, 해당 키만 설정/덮어씀
    stats['original_templates_per_masking_cnt'] = templates_per_masking_cnt

    # 6) 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)

    print(f"original_templates_per_masking_cnt가 '{output_file}'에 저장되었습니다.")
    print(f"계산된 값: {templates_per_masking_cnt}")
    

def main():
    parser = argparse.ArgumentParser(description='지정된 분포에 따라 쿼리를 생성합니다 (DB 직접 샘플링 지원).')
    
    parser.add_argument('--benchmark_type', type=str, required=True, 
                       choices=['EHRSQL', 'ScienceBenchmark', 'BIRD'],
                       help='벤치마크 타입 (EHRSQL, ScienceBenchmark 또는 BIRD)')
    
    parser.add_argument('--split', type=str, required=True,
                       choices=['Train', 'Dev', 'Combined'],
                       help='데이터 분할 (Train, Dev, 또는 Combined - Train+Dev 모두 사용)')
    
    parser.add_argument('--target_db', type=str, required=True,
                       help='대상 데이터베이스 (EHRSQL: mimic_iii 또는 eicu, ScienceBench: sdss, cordis, oncomx)')
    
    parser.add_argument('--distribution_type', type=str, required=True,
                       choices=['zipf', 'uniform'],
                       help='분포 타입 (zipf 또는 uniform)')
    
    parser.add_argument('--num_queries', type=int, required=True,
                       help='생성할 쿼리 개수')
    
    parser.add_argument('--output_file', type=str, default=None,
                       help='출력 파일명 (기본값: 자동 생성)')
    
    parser.add_argument('--distribution_file', type=str,
                       help='분포 데이터 파일 경로 (기본값: 자동 생성)')
    
    parser.add_argument('--criterion', type=str, default='rank',
                       choices=['random', 'rank', 'query_len'],
                       help='Zipf 분포에서 rank 정렬 기준 (random: 무작위, rank: cnt 기준, query_len: 질문 길이 기준, 기본값: rank)')
    
    parser.add_argument('--alpha', type=float, default=1.0,
                       help='Zipf 분포의 alpha 파라미터 (기본값: 1.0)')
    
    parser.add_argument('--power_law_s', type=float, default=2.0,
                       help='Power law 분포의 지수 s (query_len criterion에서 사용, 기본값: 2.0)')
    
    parser.add_argument('--literal_mode', type=str, default='db',
                       choices=['db'],
                       help='리터럴 값 사용 모드: db(DB에서 직접 샘플링)')
    
    parser.add_argument('--max_retries', type=int, default=10,
                       help='각 인스턴스별 최대 재시도 횟수 (기본값: 10)')
    
    parser.add_argument('--literals_file', type=str, default=None,
                       help='리터럴 데이터 파일 경로 (기본값: 자동 생성)')
    

    args = parser.parse_args()
    
    # 랜덤 시드 고정
    random.seed(42)
    np.random.seed(42)
    print("랜덤 시드가 42로 고정되었습니다.")
    
    
    # 입력 검증
    if args.benchmark_type == "EHRSQL":
        if args.target_db not in ["mimic_iii", "eicu"]:
            raise ValueError("EHRSQL의 경우 target_db는 mimic_iii 또는 eicu여야 합니다.")
    elif args.benchmark_type == "ScienceBenchmark":
        if args.target_db not in ["sdss", "cordis", "oncomx"]:
            raise ValueError("ScienceBenchmark의 경우 target_db는 sdss, cordis, 또는 oncomx여야 합니다.")
    elif args.benchmark_type == "BIRD":
        pass
    
    # 기본 파일 경로 설정
    if args.distribution_file is None:
        if args.benchmark_type == "EHRSQL":
            args.distribution_file = f"data/distribution/EHRSQL_m2.json"
        elif args.benchmark_type == "ScienceBenchmark":
            args.distribution_file = f"data/distribution/ScienceBenchmark_m2.json"
        elif args.benchmark_type == "BIRD":
            args.distribution_file = f"data/distribution/BIRD_m2.json"
    
    # 리터럴 파일 경로 설정
    if args.literals_file is None:
        if args.benchmark_type == "EHRSQL":
            args.literals_file = f"data/literals/EHRSQL_m2.json"
        elif args.benchmark_type == "ScienceBenchmark":
            args.literals_file = f"data/literals/ScienceBenchmark_m2.json"
        elif args.benchmark_type == "BIRD":
            args.literals_file = f"data/literals/BIRD_m2.json"
    

    # 출력 파일명 자동 생성
    if args.output_file is None:
        if args.distribution_type == "zipf":
            if args.criterion == "query_len":
                output_file = f"data/workload/{args.benchmark_type}_{args.split}_{args.target_db}_{args.distribution_type}_{args.criterion}_powerlaw{args.power_law_s}_n{args.num_queries}_db.json"
            else:
                output_file = f"data/workload/{args.benchmark_type}_{args.split}_{args.target_db}_{args.distribution_type}_{args.criterion}_alpha{args.alpha}_n{args.num_queries}_db.json"
        else:
            output_file = f"data/workload/{args.benchmark_type}_{args.split}_{args.target_db}_{args.distribution_type}_n{args.num_queries}_db.json"
    else:
        output_file = args.output_file
    
    # output_file의 디렉토리 생성
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # 쿼리 생성 또는 기존 파일 업데이트
    print(f"target_db: {args.target_db}")
    
    # 기존 JSON 파일에 original_templates_per_masking_cnt 필드만 추가
    update_existing_json_with_original_masking_stats(
        output_file,
        args.benchmark_type,
        args.split,
        args.target_db,
        args.distribution_type,
        args.num_queries,
        args.distribution_file,
        args.criterion,
        args.alpha,
        args.power_law_s
    )

if __name__ == "__main__":
    main()
