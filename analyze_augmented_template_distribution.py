import json
import os
import argparse
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # GUI 없이 PNG 저장용
from pathlib import Path
from collections import defaultdict

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
# 한글을 지원하는 폰트로 변경 시도
try:
    # Linux에서 일반적으로 사용 가능한 한글 폰트들
    import matplotlib.font_manager as fm
    # 한글 폰트 찾기
    font_list = [f.name for f in fm.fontManager.ttflist]
    korean_fonts = ['NanumGothic', 'NanumBarunGothic', 'Noto Sans CJK KR', 'Malgun Gothic', 'AppleGothic']
    found_font = None
    for font in korean_fonts:
        if font in font_list:
            found_font = font
            break
    
    if found_font:
        plt.rcParams['font.family'] = found_font
        print(f"한글 폰트 설정: {found_font}")
    else:
        # 폰트를 찾지 못한 경우 경고만 출력하고 계속 진행
        print("⚠️  한글 폰트를 찾을 수 없습니다. 한글이 깨져 보일 수 있습니다.")
except Exception as e:
    print(f"⚠️  폰트 설정 중 오류 발생: {e}")

def load_workload_json(file_path):
    """워크로드 JSON 파일을 로드하고 queries와 statistics를 반환합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('queries', []), data.get('statistics', {})
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None, None

def aggregate_augmented_template_per_template_id(queries):
    """queries에서 template_id별로 사용된 augmented template 종류 개수를 집계합니다.
    
    Args:
        queries: 쿼리 리스트
        
    Returns:
        template_id -> set of augmented_template_ids 구조
        template_id -> workload_count 구조
    """
    # template_id -> set of augmented_template_ids
    template_augmented_map = defaultdict(set)
    # template_id -> workload count
    template_workload_count = defaultdict(int)
    
    for query in queries:
        template_id = query.get('template_id')
        if template_id is None:
            continue
        
        template_workload_count[template_id] += 1
        
        # augmented template이 있는 경우
        if query.get('is_augmented', False):
            augmented_template_id = query.get('augmented_template_id')
            if augmented_template_id is not None:
                template_augmented_map[template_id].add(augmented_template_id)
    
    return template_augmented_map, template_workload_count

def compute_distribution(template_augmented_map, template_workload_count):
    """Augmented template 종류 개수별 분포를 계산합니다.
    
    Args:
        template_augmented_map: template_id -> set of augmented_template_ids
        template_workload_count: template_id -> workload count
        
    Returns:
        augmented_count -> {
            'template_id_count': 해당 개수를 가진 template_id 수,
            'total_workload_count': 해당 개수를 가진 template_id들이 생성한 총 workload 수
        }
    """
    distribution = defaultdict(lambda: {'template_id_count': 0, 'total_workload_count': 0})
    
    # 모든 template_id에 대해 처리
    all_template_ids = set(template_augmented_map.keys()) | set(template_workload_count.keys())
    
    for template_id in all_template_ids:
        # 해당 template_id가 사용한 augmented template 종류 개수
        augmented_count = len(template_augmented_map.get(template_id, set()))
        workload_count = template_workload_count.get(template_id, 0)
        
        distribution[augmented_count]['template_id_count'] += 1
        distribution[augmented_count]['total_workload_count'] += workload_count
    
    return distribution

def plot_template_id_count(distribution, output_path, db_name, benchmark_type, dist_type):
    """Augmented template 종류 개수별 Template ID 개수를 시각화합니다.
    
    Args:
        distribution: augmented_count별 분포 데이터
        output_path: 출력 파일 경로
        db_name: 데이터베이스 이름
        benchmark_type: 벤치마크 타입
        dist_type: distribution 타입 (uniform, zipf_random, zipf_query_len 등)
    """
    if not distribution:
        print(f"  ⚠️  {db_name}: No distribution data. Skipping...")
        return
    
    # augmented_count를 정렬
    augmented_counts = sorted(distribution.keys())
    
    # 데이터 추출
    template_id_counts = [distribution[ac]['template_id_count'] for ac in augmented_counts]
    
    # 그래프 생성
    fig, ax = plt.subplots(figsize=(12, 6))
    
    color = '#FF6B6B'
    ax.set_xlabel('Number of Augmented Template Types', fontsize=12)
    ax.set_ylabel('Number of Template IDs', fontsize=12)
    bars = ax.bar(range(len(augmented_counts)), template_id_counts, 
                  width=0.6, label='Number of Template IDs', alpha=0.8, color=color)
    ax.set_xticks(range(len(augmented_counts)))
    ax.set_xticklabels([str(ac) for ac in augmented_counts])
    ax.grid(axis='y', alpha=0.3)
    ax.legend()
    
    # 제목 설정
    dist_type_title = dist_type.replace('_', ' ').title()
    ax.set_title(f'{benchmark_type} - {db_name} ({dist_type_title})\nNumber of Template IDs by Number of Augmented Template Types', 
                 fontsize=14, fontweight='bold')
    
    # 값 레이블 추가
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

def plot_workload_count(distribution, output_path, db_name, benchmark_type, dist_type):
    """Augmented template 종류 개수별 총 Workload 수를 시각화합니다.
    
    Args:
        distribution: augmented_count별 분포 데이터
        output_path: 출력 파일 경로
        db_name: 데이터베이스 이름
        benchmark_type: 벤치마크 타입
        dist_type: distribution 타입 (uniform, zipf_random, zipf_query_len 등)
    """
    if not distribution:
        print(f"  ⚠️  {db_name}: No distribution data. Skipping...")
        return
    
    # augmented_count를 정렬
    augmented_counts = sorted(distribution.keys())
    
    # 데이터 추출
    total_workload_counts = [distribution[ac]['total_workload_count'] for ac in augmented_counts]
    
    # 그래프 생성
    fig, ax = plt.subplots(figsize=(12, 6))
    
    color = '#4ECDC4'
    ax.set_xlabel('Number of Augmented Template Types', fontsize=12)
    ax.set_ylabel('Total Workload Count', fontsize=12)
    bars = ax.bar(range(len(augmented_counts)), total_workload_counts, 
                  width=0.6, label='Total Workload Count', alpha=0.8, color=color)
    ax.set_xticks(range(len(augmented_counts)))
    ax.set_xticklabels([str(ac) for ac in augmented_counts])
    ax.grid(axis='y', alpha=0.3)
    ax.legend()
    
    # 제목 설정
    dist_type_title = dist_type.replace('_', ' ').title()
    ax.set_title(f'{benchmark_type} - {db_name} ({dist_type_title})\nTotal Workload Count by Number of Augmented Template Types', 
                 fontsize=14, fontweight='bold')
    
    # 값 레이블 추가
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
    parser = argparse.ArgumentParser(description='Analyze augmented template distribution per template_id')
    parser.add_argument('--base-dir', type=str, 
                       default="/data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/data/workloads_v17_1k",
                       help='Base directory for workload data (should contain Dev and Train subdirectories)')
    parser.add_argument('--output-dir', type=str,
                       default="/data/yhyunjun/HybridSQL-Benchmark/workload-construction-2/tools/augmented_template_distribution_plots/v17",
                       help='Output directory for plots')
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir)
    output_dir = Path(args.output_dir)
    
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
                    queries, stats = load_workload_json(workload_file)
                    if queries is None:
                        continue
                    
                    # 분포 데이터 집계
                    template_augmented_map, template_workload_count = aggregate_augmented_template_per_template_id(queries)
                    distribution = compute_distribution(template_augmented_map, template_workload_count)
                    
                    if not distribution:
                        print(f"    ⚠️  {dist_type}: 분포 데이터 없음. 건너뜀...")
                        continue
                    
                    # split/distribution 타입별 출력 디렉토리 생성 (Template ID 개수용)
                    template_id_output_dir = output_dir / "template_id_count" / split / dist_type
                    template_id_output_dir.mkdir(exist_ok=True, parents=True)
                    
                    # split/distribution 타입별 출력 디렉토리 생성 (Workload 수용)
                    workload_output_dir = output_dir / "workload_count" / split / dist_type
                    workload_output_dir.mkdir(exist_ok=True, parents=True)
                    
                    # Template ID 개수 그래프 생성
                    template_id_output_path = template_id_output_dir / f"{dataset}_{db_name}_augmented_template_distribution.png"
                    plot_template_id_count(distribution, template_id_output_path, db_name, dataset, dist_type)
                    
                    # Workload 수 그래프 생성
                    workload_output_path = workload_output_dir / f"{dataset}_{db_name}_augmented_template_distribution.png"
                    plot_workload_count(distribution, workload_output_path, db_name, dataset, dist_type)
                    
                    total_plots += 2
                    print(f"    ✅ {dist_type}: 완료")
    
    print(f"\n{'=' * 60}")
    print(f"🎉 총 {total_plots}개 plot이 저장되었습니다: {output_dir}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()

