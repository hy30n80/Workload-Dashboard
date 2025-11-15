#!/usr/bin/env python3
"""
initial_distribution과 generated_distribution을 비교하는 plot을 생성합니다.
모든 distribution 타입(uniform, zipf_random, zipf_query_len 등)에 대해 plot을 생성합니다.
"""

import json
import os
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # GUI 없이 사용

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
        "Dev": ["debit_card_specializing"]
    },
    "Financial": {
        "Train": ["student_loan"],
        "Dev": ["debit_card_specializing"]
    }
}

def load_distribution_file(file_path):
    """분포 JSON 파일을 로드합니다."""
    if not os.path.exists(file_path):
        print(f"Warning: 파일을 찾을 수 없습니다: {file_path}")
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data

def get_sorted_counts(template_distribution):
    """template_distribution을 내림차순으로 정렬하여 count 리스트를 반환합니다."""
    if not template_distribution:
        return []
    
    # 값(CNT)만 추출하여 내림차순 정렬
    counts = sorted(template_distribution.values(), reverse=True)
    return counts

def find_all_distributions(data):
    """모든 distribution 타입을 찾아서 경로와 분포를 반환합니다."""
    all_distributions = []
    
    # Train-BIRD의 개별 DB 이름들 수집 (Train에서만 제외할 목록)
    # Dev는 그대로 유지
    all_train_dbs = []
    for domain_info in BIRD_DOMAIN_DBS.values():
        all_train_dbs.extend(domain_info["Train"])
    
    for split in data.keys():
        if not isinstance(data[split], dict):
            continue
        
        for benchmark_type in data[split].keys():
            if not isinstance(data[split][benchmark_type], dict):
                continue
            
            for target_db in data[split][benchmark_type].keys():
                if not isinstance(data[split][benchmark_type][target_db], dict):
                    continue
                
                # Train-BIRD의 경우에만 개별 DB 이름 제외 (domain 이름만 처리)
                # Dev-BIRD는 개별 DB 이름도 그대로 포함
                if split == "Train" and benchmark_type == "BIRD" and target_db in all_train_dbs:
                    continue
                
                # 모든 distribution 타입 찾기 (uniform, zipf_random, zipf_query_len 등)
                for dist_key, dist_data in data[split][benchmark_type][target_db].items():
                    if isinstance(dist_data, dict) and "template_distribution" in dist_data:
                        all_distributions.append({
                            "split": split,
                            "benchmark_type": benchmark_type,
                            "target_db": target_db,
                            "distribution_key": dist_key,
                            "template_distribution": dist_data["template_distribution"]
                        })
    
    return all_distributions

def plot_comparison(initial_counts, generated_counts, output_path, title):
    """두 분포를 비교하는 plot을 생성합니다."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # X축: template 순서 (1부터 시작)
    x_initial = range(1, len(initial_counts) + 1) if initial_counts else []
    x_generated = range(1, len(generated_counts) + 1) if generated_counts else []
    
    # Plot 생성
    if initial_counts:
        ax.plot(x_initial, initial_counts, 'r-', linewidth=1.5, label='Initial Distribution', alpha=0.7)
        ax.scatter(x_initial, initial_counts, c='red', s=10, alpha=0.5)
    
    if generated_counts:
        ax.plot(x_generated, generated_counts, 'b-', linewidth=1.5, label='Generated Distribution', alpha=0.7)
        ax.scatter(x_generated, generated_counts, c='blue', s=10, alpha=0.5)
    
    ax.set_xlabel('Template Rank (sorted by count, descending)', fontsize=12)
    ax.set_ylabel('Count (CNT)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✅ Plot 저장됨: {output_path}")

def main():
    initial_file = "tools/distribution/initial_distribution.json"
    generated_file = "tools/distribution/generated_distribution.json"
    base_output_dir = "tools/distribution_plots"
    
    print("=" * 60)
    print("Distribution Comparison Plot 생성 시작")
    print("=" * 60)
    
    # 파일 로드
    print("분포 파일 로드 중...")
    initial_data = load_distribution_file(initial_file)
    generated_data = load_distribution_file(generated_file)
    
    if initial_data is None or generated_data is None:
        print("❌ 분포 파일을 로드할 수 없습니다.")
        return
    
    # 모든 distribution 타입 찾기
    print("모든 distribution 타입 찾는 중...")
    initial_dists = find_all_distributions(initial_data)
    generated_dists = find_all_distributions(generated_data)
    
    print(f"Initial: {len(initial_dists)}개 distribution 발견")
    print(f"Generated: {len(generated_dists)}개 distribution 발견")
    
    # generated_dists를 딕셔너리로 변환 (빠른 검색을 위해)
    # key: (split, benchmark_type, target_db, distribution_key)
    generated_dict = {}
    for gen in generated_dists:
        key = (gen["split"], gen["benchmark_type"], gen["target_db"], gen["distribution_key"])
        generated_dict[key] = gen["template_distribution"]
    
    # distribution 타입별로 그룹화하여 출력 디렉토리 생성
    distribution_types = {}
    for init in initial_dists:
        dist_key = init["distribution_key"]
        if dist_key not in distribution_types:
            distribution_types[dist_key] = []
        distribution_types[dist_key].append(init)
    
    print(f"\n발견된 distribution 타입: {list(distribution_types.keys())}")
    
    # split별로 그룹화
    split_groups = {}
    for init in initial_dists:
        split = init["split"]
        if split not in split_groups:
            split_groups[split] = {}
        dist_key = init["distribution_key"]
        if dist_key not in split_groups[split]:
            split_groups[split][dist_key] = []
        split_groups[split][dist_key].append(init)
    
    # 각 split별로 plot 생성
    total_plot_count = 0
    for split in ["Dev", "Train"]:
        if split not in split_groups:
            continue
        
        print(f"\n{'=' * 60}")
        print(f"🔹 Processing {split} split...")
        print(f"{'=' * 60}")
        
        for dist_key, dists in split_groups[split].items():
            print(f"\n  {dist_key} 분포 처리 중... ({len(dists)}개)")
            
            # split/distribution 타입별 출력 디렉토리 생성
            output_dir = os.path.join(base_output_dir, split, dist_key)
            os.makedirs(output_dir, exist_ok=True)
            
            plot_count = 0
            for init in dists:
                benchmark_type = init["benchmark_type"]
                target_db = init["target_db"]
                key = (split, benchmark_type, target_db, dist_key)
                
                # Initial 분포의 count 추출 (내림차순)
                initial_counts = get_sorted_counts(init["template_distribution"])
                
                # Generated 분포 찾기
                generated_counts = []
                if key in generated_dict:
                    generated_counts = get_sorted_counts(generated_dict[key])
                else:
                    # zipf_query_len과 zipf_query 매칭 처리
                    if dist_key == "zipf_query_len":
                        alt_key = (split, benchmark_type, target_db, "zipf_query")
                        if alt_key in generated_dict:
                            generated_counts = get_sorted_counts(generated_dict[alt_key])
                        else:
                            print(f"    ⚠️ Generated 분포를 찾을 수 없음: {split}/{benchmark_type}/{target_db}/{dist_key} (또는 zipf_query)")
                    elif dist_key == "zipf_query":
                        alt_key = (split, benchmark_type, target_db, "zipf_query_len")
                        if alt_key in generated_dict:
                            generated_counts = get_sorted_counts(generated_dict[alt_key])
                        else:
                            print(f"    ⚠️ Generated 분포를 찾을 수 없음: {split}/{benchmark_type}/{target_db}/{dist_key} (또는 zipf_query_len)")
                    else:
                        print(f"    ⚠️ Generated 분포를 찾을 수 없음: {split}/{benchmark_type}/{target_db}/{dist_key}")
                
                # Plot 생성
                title = f"{split}/{benchmark_type}/{target_db} - {dist_key.title()} Distribution"
                safe_title = title.replace("/", "_").replace(" ", "_")
                output_path = os.path.join(output_dir, f"{safe_title}.png")
                
                plot_comparison(initial_counts, generated_counts, output_path, title)
                plot_count += 1
                total_plot_count += 1
            
            print(f"    ✅ {dist_key}: {plot_count}개 plot 생성 완료")
    
    print("\n" + "=" * 60)
    print(f"✅ 총 {total_plot_count}개 plot 생성 완료!")
    print(f"출력 디렉토리: {base_output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()

