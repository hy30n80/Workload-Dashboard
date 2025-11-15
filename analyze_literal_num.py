import json
import os
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # GUI 없이 PNG 저장용
import numpy as np
from pathlib import Path

def load_workload_json(file_path):
    """워크로드 JSON 파일을 로드하고 statistics를 반환합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('statistics', {})
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def plot_distribution(queries_dist, templates_dist, output_path, db_name, benchmark_type, dist_type):
    """두 분포를 비교해서 막대 그래프로 시각화합니다."""
    # 키를 정수로 변환하고 정렬
    queries_keys = sorted([int(k) for k in queries_dist.keys()])
    templates_keys = sorted([int(k) for k in templates_dist.keys()])
    
    # 모든 키를 포함하는 집합
    all_keys = sorted(set(templates_keys + queries_keys))
    
    # 값 추출 (없는 키는 0)
    templates_values = [templates_dist.get(str(k), 0) for k in all_keys]
    queries_values = [queries_dist.get(str(k), 0) for k in all_keys]
    
    # 그래프 생성
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(all_keys))
    width = 0.35
    # 막대 그래프 그리기
    bars1 = ax.bar(x - width/2, templates_values, width, label='Sampled templates', alpha=0.8, color='lightcoral')
    bars2 = ax.bar(x + width/2, queries_values, width, label='Generated templates', alpha=0.8, color='skyblue')
    
    # 레이블 설정
    ax.set_xlabel('Masking Count', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    dist_type_title = dist_type.replace('_', ' ').title()
    ax.set_title(f'{benchmark_type} - {db_name} ({dist_type_title})\nLiteral Distribution Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(all_keys)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # 값 레이블 추가
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")

def main():
    base_dir = Path("/data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/data/workloads_v16_1k")
    output_dir = Path("/data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/tools/literal_distribution_plots/v16")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    datasets = ["BIRD", "EHRSQL", "ScienceBenchmark"]
    splits = ["Dev", "Train"]
    
    # 모든 distribution 타입 정의
    distribution_types = [
        ("uniform_rank", "uniform"),
        ("zipf_random", "zipf_random"),
        ("zipf_query_len", "zipf_query_len")
    ]
    
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
                    stats = load_workload_json(workload_file)
                    if stats is None:
                        continue
                    
                    # 분포 데이터 추출
                    queries_dist = stats.get('queries_per_masking_cnt', {})
                    templates_dist = stats.get('original_templates_per_masking_cnt', {})
                    
                    if not queries_dist or not templates_dist:
                        print(f"    ⚠️  {dist_type}: 분포 데이터 없음. 건너뜀...")
                        continue
                    
                    # split/distribution 타입별 출력 디렉토리 생성
                    split_output_dir = output_dir / split / dist_type
                    split_output_dir.mkdir(exist_ok=True, parents=True)
                    
                    # 그래프 생성
                    output_path = split_output_dir / f"{dataset}_{db_name}_literal_distribution.png"
                    plot_distribution(queries_dist, templates_dist, output_path, db_name, dataset, dist_type)
                    
                    total_plots += 1
                    print(f"    ✅ {dist_type}: 완료")
    
    print(f"\n{'=' * 60}")
    print(f"🎉 총 {total_plots}개 plot이 저장되었습니다: {output_dir}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()





