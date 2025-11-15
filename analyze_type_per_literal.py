import json
import os
import argparse
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # GUI 없이 PNG 저장용
import numpy as np
from pathlib import Path
from collections import defaultdict

def load_workload_json(file_path):
    """워크로드 JSON 파일을 로드하고 queries와 statistics를 반환합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('queries', []), data.get('statistics', {})
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None, None

def normalize_sampling_method(method, group_mode=False):
    """sampling_method를 그룹화 모드에 따라 정규화합니다.
    
    Args:
        method: 원본 sampling_method
        group_mode: True이면 그룹화, False이면 원본 유지
        
    Returns:
        정규화된 sampling_method
    """
    if not group_mode:
        return method
    
    # 그룹화 모드: "db", "histogram" → "DB", 나머지 → "EXISTING"
    if method in ["db", "histogram"]:
        return "DB"
    else:
        return "EXISTING"

def aggregate_sampling_method_per_masking_cnt(queries, group_mode=False):
    """queries에서 masking_cnt별 sampling_method 분포를 집계합니다.
    
    Args:
        queries: 쿼리 리스트
        group_mode: True이면 sampling_method를 그룹화 (db/histogram → DB, 나머지 → EXISTING)
    """
    # masking_cnt -> {sampling_method: count} 구조로 저장
    distribution = defaultdict(lambda: defaultdict(int))
    
    for query in queries:
        masking_cnt = query.get('masking_cnt', 0)
        sampling_method = query.get('sampling_method', 'unknown')
        # 그룹화 모드 적용
        normalized_method = normalize_sampling_method(sampling_method, group_mode)
        distribution[masking_cnt][normalized_method] += 1
    
    return distribution

def plot_sampling_method_distribution(distribution, output_path, db_name, benchmark_type, dist_type, method_order=None, group_mode=True):
    """masking_cnt별 sampling_method 분포를 막대 그래프로 시각화합니다.
    
    Args:
        distribution: masking_cnt별 sampling_method 분포 데이터
        output_path: 출력 파일 경로
        db_name: 데이터베이스 이름
        benchmark_type: 벤치마크 타입
        dist_type: distribution 타입 (uniform, zipf_random, zipf_query_len 등)
        method_order: sampling_method 순서 리스트 (None이면 알파벳 순서로 정렬)
        group_mode: True이면 그룹화 모드 (db/histogram → DB, 나머지 → EXISTING)
    """
    if not distribution:
        print(f"  ⚠️  {db_name}: No distribution data. Skipping...")
        return
    
    # masking_cnt를 정렬하고 sampling_method 목록 수집
    masking_cnts = sorted(distribution.keys())
    all_sampling_methods_set = set()
    for cnt_dict in distribution.values():
        all_sampling_methods_set.update(cnt_dict.keys())
    
    # method_order 설정
    if group_mode:
        # 그룹화 모드: DB, EXISTING 순서
        method_order = ["DB", "EXISTING"]
    else:
        # 원본 모드: 기본 순서
        method_order = ["original", "db", "histogram", "existing", "example_value"]
    
    if method_order is not None:
        # method_order에 있는 것만 포함하고, 순서 유지
        all_sampling_methods = [m for m in method_order if m in all_sampling_methods_set]
        # method_order에 없는 것들은 뒤에 추가
        remaining = sorted([m for m in all_sampling_methods_set if m not in method_order])
        all_sampling_methods = all_sampling_methods + remaining
    else:
        all_sampling_methods = sorted(all_sampling_methods_set)
    
    if not all_sampling_methods:
        print(f"  ⚠️  {db_name}: No sampling methods found. Skipping...")
        return
    
    # 각 sampling_method별로 masking_cnt에 따른 값 추출
    method_data = {}
    for method in all_sampling_methods:
        method_data[method] = [distribution.get(mc, {}).get(method, 0) for mc in masking_cnts]
    
    # 그래프 생성
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 각 그룹 사이에 간격을 주기 위해 x축 위치를 조정
    group_spacing = 1.2  # 그룹 간 간격 (1.0보다 크면 간격이 생김)
    x = np.arange(len(masking_cnts)) * group_spacing
    width = 0.2  # sampling_method 개수에 따라 조정 가능
    
    # 색상 팔레트 (sampling_method 개수에 따라 자동 조정)
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']
    if len(all_sampling_methods) > len(colors):
        # 더 많은 색상이 필요하면 추가
        import matplotlib.cm as cm
        colors = cm.tab20(np.linspace(0, 1, len(all_sampling_methods)))
    
    # 각 sampling_method별 막대 그래프 그리기
    bars_list = []
    for idx, method in enumerate(all_sampling_methods):
        offset = (idx - len(all_sampling_methods)/2 + 0.5) * width
        bars = ax.bar(x + offset, method_data[method], width, 
                     label=method, alpha=0.8, color=colors[idx % len(colors)])
        bars_list.append(bars)
    
    # 레이블 설정
    ax.set_xlabel('Masking Count', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    dist_type_title = dist_type.replace('_', ' ').title()
    ax.set_title(f'{benchmark_type} - {db_name} ({dist_type_title})\nSampling Method Distribution per Masking Count', 
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([str(mc) for mc in masking_cnts])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # 값 레이블 추가
    for bars in bars_list:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")

def main(): 
    parser = argparse.ArgumentParser(description='Analyze sampling method distribution per masking count')
    parser.add_argument('--group-mode', action='store_true', 
                       help='Group sampling methods: db/histogram → DB, others → EXISTING')
    parser.add_argument('--base-dir', type=str, 
                       default="/data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/data/workloads_v16_1k",
                       help='Base directory for workload data (should contain Dev and Train subdirectories)')
    parser.add_argument('--output-dir', type=str,
                       default="/data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/tools/sampling_method_distribution_plots/v17",
                       help='Output directory for plots')
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir)
    output_dir = Path(args.output_dir)
    group_mode = args.group_mode
    
    # 그룹화 모드에 따라 출력 디렉토리 이름 변경
    if group_mode:
        output_dir = output_dir.parent / f"{output_dir.name}"
    
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # sampling_method 순서 지정 (None이면 알파벳 순서로 정렬)
    method_order = None
    
    datasets = ["BIRD", "EHRSQL", "ScienceBenchmark"]
    splits = ["Dev", "Train"]
    
    # 모든 distribution 타입 정의
    distribution_types = [
        ("uniform_rank", "uniform"),
        ("zipf_random", "zipf_random"),
        ("zipf_query_len", "zipf_query_len")
    ]

    # v10 용
    # distribution_types = [
    #     ("uniform", "uniform"),
    #     ("zipf(random)", "zipf_random"),
    #     ("zipf(query_len)", "zipf_query_len")
    # ]
    
    if group_mode:
        print("🔹 그룹화 모드 활성화: db/histogram → DB, 나머지 → EXISTING")
    else:
        print("🔹 원본 모드: sampling_method 그룹화 없음")
    
    total_plots = 0
    
    # Dev와 Train 모두 처리
    for split in splits:
        split_dir = base_dir / split
        if not split_dir.exists():
            print(f"Warning: {split_dir} does not exist. Skipping...")
            continue
        
        print(f"\n{'=' * 60}")
        print(f"🔹 Processing {split} split...")
        print(f"{'=' * 60}")
        
        for dataset in datasets:
            dataset_path = split_dir / dataset
            if not dataset_path.exists():
                print(f"Warning: {dataset_path} does not exist. Skipping...")
                continue
            
            print(f"\n🔹 Processing {split}/{dataset}...")
            
            # 각 DB 디렉토리 탐색
            for db_dir in dataset_path.iterdir():
                if not db_dir.is_dir():
                    continue
                
                db_name = db_dir.name
                print(f"\n  📁 {db_name}:")
                
                # 각 distribution 타입 처리
                for file_pattern, dist_type in distribution_types:
                    workload_file = db_dir / f"{file_pattern}_1k.json"
                    
                    if not workload_file.exists():
                        print(f"    ⚠️  {dist_type}: 파일을 찾을 수 없음. 건너뜀...")
                        continue
                    
                    # JSON 파일 로드
                    queries, stats = load_workload_json(workload_file)
                    if queries is None:
                        continue
                    
                    # 분포 데이터 집계
                    distribution = aggregate_sampling_method_per_masking_cnt(queries, group_mode=group_mode)
                    
                    if not distribution:
                        print(f"    ⚠️  {dist_type}: 분포 데이터 없음. 건너뜀...")
                        continue
                    
                    # split/distribution 타입별 출력 디렉토리 생성
                    split_output_dir = output_dir / split / dist_type
                    split_output_dir.mkdir(exist_ok=True, parents=True)
                    
                    # 그래프 생성
                    suffix = "_grouped" if group_mode else ""
                    output_path = split_output_dir / f"{dataset}_{db_name}_sampling_method_distribution{suffix}.png"
                    plot_sampling_method_distribution(distribution, output_path, db_name, dataset, dist_type, method_order, group_mode=group_mode)
                    
                    total_plots += 1
                    print(f"    ✅ {dist_type}: 완료")
    
    print(f"\n{'=' * 60}")
    print(f"🎉 총 {total_plots}개 plot이 저장되었습니다: {output_dir}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()

