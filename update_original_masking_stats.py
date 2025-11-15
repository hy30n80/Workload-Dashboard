#!/usr/bin/env python3
"""
기존 결과 JSON을 훼손하지 않고, original_templates_per_masking_cnt 통계만 계산해 삽입하는 스크립트.
- query_generator_db.py의 로더/샘플러를 이용해 원래와 동일한 샘플링으로 counts만 계산
- 기본적으로 새로운 파일로 저장(_with_orig_masking.json). --in_place로 원본에 덮어쓰기 가능

필수 파라미터 (원 실행과 동일해야 동일한 샘플링 재현):
  --benchmark_type {EHRSQL|ScienceBenchmark|BIRD}
  --split {Train|Dev|Combined}
  --target_db <예: eicu|mimic_iii|sdss|cordis|oncomx|...>
  --distribution_type {zipf|uniform}
  --num_queries <원 실행과 동일>
  --distribution_file <원 실행에 사용한 분포 파일>
  --criterion <zipf일 때 사용: random|rank|query_len>
  --alpha <zipf-rank/random일 때 사용>
  --power_law_s <zipf-query_len일 때 사용>
  --result_file <갱신할 기존 결과 JSON 경로>
  [--in_place]  원본 파일에 덮어쓰기 (주의)

예:
  python tools/update_original_masking_stats.py \
    --benchmark_type BIRD --split Dev --target_db codebase_community \
    --distribution_type zipf --criterion rank --alpha 1.0 --num_queries 1000 \
    --distribution_file data/distribution/BIRD_m2.json \
    --result_file bird_results_full/codebase_community_results.json
"""

import json
import os
import argparse
from typing import Dict

# 같은 디렉토리 구조에서 import
from src.workload-generator.query_generator_db import (
    load_distribution_data,
    load_combined_distribution_data,
    sample_templates_zipf,
    sample_templates_uniform,
)

def compute_original_masking_counts(sampled_templates) -> Dict[int, int]:
    """샘플된 템플릿들로 original_templates_per_masking_cnt 계산."""
    templates_per_masking_cnt: Dict[int, int] = {}
    for template in sampled_templates:
        masking_cnt = 0
        mask_type = "m2"
        # literals 길이를 기준으로 [m2_i] 마스크가 question_semi_template(리스트 가능) 내 포함 여부 확인
        qst = template.get("question_semi_template")
        if isinstance(qst, list):
            base_qst = qst[0] if qst else ""
        else:
            base_qst = qst or ""
        for idx in range(len(template.get("literals", []))):
            mask_pattern = f"[{mask_type}_{idx}]"
            if mask_pattern in base_qst:
                masking_cnt += 1
        templates_per_masking_cnt[masking_cnt] = templates_per_masking_cnt.get(masking_cnt, 0) + 1
    return templates_per_masking_cnt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--benchmark_type', required=True, choices=['EHRSQL','ScienceBenchmark','BIRD'])
    ap.add_argument('--split', required=True, choices=['Train','Dev','Combined'])
    ap.add_argument('--target_db', required=True)
    ap.add_argument('--distribution_type', required=True, choices=['zipf','uniform'])
    ap.add_argument('--num_queries', required=True, type=int)
    ap.add_argument('--distribution_file', required=True)
    ap.add_argument('--criterion', default='rank', choices=['random','rank','query_len'])
    ap.add_argument('--alpha', type=float, default=1.0)
    ap.add_argument('--power_law_s', type=float, default=2.0)
    ap.add_argument('--result_file', required=True)
    ap.add_argument('--in_place', action='store_true')
    args = ap.parse_args()

    # 1) 기존 결과 파일 로드
    with open(args.result_file, 'r', encoding='utf-8') as f:
        result_data = json.load(f)
    
    # 기존 파일에 이미 해당 필드가 있는지 확인
    if 'statistics' in result_data and 'original_templates_per_masking_cnt' in result_data['statistics']:
        print(f"Warning: {args.result_file}에 이미 'original_templates_per_masking_cnt' 필드가 있습니다.")
        print("기존 값을 덮어씁니다.")

    # 2) 분포 데이터 로드 (원 실행과 동일하게)
    if args.split == 'Combined':
        templates = load_combined_distribution_data(args.distribution_file, args.benchmark_type, args.target_db)
    else:
        templates = load_distribution_data(args.distribution_file, args.benchmark_type, args.split, args.target_db)

    # 3) 동일 분포로 샘플링
    if args.distribution_type == 'zipf':
        sampled_templates = sample_templates_zipf(templates, args.num_queries, args.criterion, args.alpha, args.power_law_s)
    else:
        sampled_templates = sample_templates_uniform(templates, args.num_queries)

    # 4) original_templates_per_masking_cnt 계산
    orig_counts = compute_original_masking_counts(sampled_templates)

    # 5) 기존 결과에 필드만 주입
    stats = result_data.setdefault('statistics', {})
    # 기존 키는 절대 건드리지 않고, 해당 키만 설정/덮어씀
    stats['original_templates_per_masking_cnt'] = orig_counts

    # 6) 저장: 기본은 새로운 파일명으로 저장
    if args.in_place:
        out_path = args.result_file
    else:
        base, ext = os.path.splitext(args.result_file)
        out_path = f"{base}_with_orig_masking{ext}"

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)

    print(f"original_templates_per_masking_cnt가 '{out_path}'에 저장되었습니다.")
    print(f"계산된 값: {orig_counts}")

if __name__ == '__main__':
    main()
