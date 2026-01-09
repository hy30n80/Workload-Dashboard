import streamlit as st
import os
from pathlib import Path
from typing import List, Optional

# 기본 경로 설정 (상대 경로 사용)
BASE_DIR = Path(__file__).parent

# Plot 디렉토리 경로
DISTRIBUTION_PLOTS_DIR = BASE_DIR / "distribution_plots"
SAMPLING_METHOD_PLOTS_DIR = BASE_DIR / "sampling_method_distribution_plots"
AUGMENTED_TEMPLATE_PLOTS_DIR = BASE_DIR / "augmented_template_distribution_plots"

# BIRD Dev split의 DB 이름 -> 도메인 이름 매핑
BIRD_DEV_DB_TO_DOMAIN = {
    "student_club": "University",
    "formula_1": "Sport",
    "codebase_community": "Software",
    "debit_card_specializing": "Financial"
}

# BIRD 도메인 이름 -> DB 이름 역매핑 (여러 DB가 하나의 도메인에 속할 수 있음)
BIRD_DOMAIN_TO_DBS = {
    "University": ["student_club"],
    "Sport": ["formula_1"],
    "Software": ["codebase_community"],
    "Financial": ["debit_card_specializing"]
}

# 사용 가능한 버전 목록 (디렉토리에서 자동 감지)
def get_available_versions() -> List[str]:
    """사용 가능한 버전 목록을 반환합니다."""
    versions = set()
    
    # 각 plot 디렉토리에서 버전 확인
    for plot_dir in [DISTRIBUTION_PLOTS_DIR, SAMPLING_METHOD_PLOTS_DIR, AUGMENTED_TEMPLATE_PLOTS_DIR]:
        if plot_dir.exists():
            for item in plot_dir.iterdir():
                if item.is_dir() and item.name.startswith('v'):
                    versions.add(item.name)
    
    return sorted(list(versions), reverse=True)  # 최신 버전부터

# 버전이 v7 이상인지 확인 (함수 정의 순서를 위해 앞에 배치)
def is_version_v7_or_above(version: str) -> bool:
    """버전이 v7 이상인지 확인합니다."""
    try:
        version_num = int(version.lstrip('v'))
        return version_num >= 7
    except ValueError:
        return False

# 사용 가능한 split 목록
def get_available_splits(version: str) -> List[str]:
    """특정 버전에서 사용 가능한 split 목록을 반환합니다."""
    splits = set()
    
    # sampling_method_distribution_plots에서 확인
    plot_dir = SAMPLING_METHOD_PLOTS_DIR / version
    if plot_dir.exists():
        for item in plot_dir.iterdir():
            if item.is_dir() and item.name in ["Dev", "Train"]:
                splits.add(item.name)
    
    # distribution_plots에서 확인
    dist_dir = DISTRIBUTION_PLOTS_DIR / version
    if dist_dir.exists():
        for item in dist_dir.iterdir():
            if item.is_dir() and item.name in ["Dev", "Train"]:
                splits.add(item.name)
    
    # augmented_template_distribution_plots에서 확인 (v7 이상)
    if is_version_v7_or_above(version):
        aug_dir = AUGMENTED_TEMPLATE_PLOTS_DIR / version / "template_id_count"
        if aug_dir.exists():
            for item in aug_dir.iterdir():
                if item.is_dir() and item.name in ["Dev", "Train"]:
                    splits.add(item.name)
    
    return sorted(list(splits))

# 사용 가능한 distribution 타입 목록
def get_available_distributions(version: str, split: str) -> List[str]:
    """특정 버전과 split에서 사용 가능한 distribution 타입 목록을 반환합니다."""
    distributions = set()
    
    # sampling_method_distribution_plots에서 확인 (v10 구조: version/split/distribution/)
    plot_dir = SAMPLING_METHOD_PLOTS_DIR / version / split
    if plot_dir.exists():
        for item in plot_dir.iterdir():
            if item.is_dir():
                distributions.add(item.name)
    
    # distribution plots에서 확인 (v10 구조: version/split/distribution/)
    dist_dir = DISTRIBUTION_PLOTS_DIR / version / split
    if dist_dir.exists():
        for item in dist_dir.iterdir():
            if item.is_dir():
                distributions.add(item.name)
    
    # v16 이전 구조 호환성 (version/distribution/ - split이 파일명에 포함)
    dist_dir_old = DISTRIBUTION_PLOTS_DIR / version
    if dist_dir_old.exists():
        for item in dist_dir_old.iterdir():
            if item.is_dir() and item.name in ["uniform", "zipf_query_len", "zipf_random"]:
                distributions.add(item.name)
    
    # augmented_template_distribution_plots에서 확인 (v7 이상)
    if is_version_v7_or_above(version):
        aug_dir = AUGMENTED_TEMPLATE_PLOTS_DIR / version / "template_id_count" / split
        if aug_dir.exists():
            for item in aug_dir.iterdir():
                if item.is_dir():
                    distributions.add(item.name)
    
    return sorted(list(distributions))

# 사용 가능한 benchmark와 DB 목록
def get_available_benchmarks_and_dbs(version: str, split: str, distribution: str) -> dict:
    """특정 설정에서 사용 가능한 benchmark와 DB 목록을 반환합니다."""
    benchmarks_dbs = {}
    
    # 1. sampling_method_distribution_plots에서 파일명 파싱
    sampling_dir = SAMPLING_METHOD_PLOTS_DIR / version / split / distribution
    if sampling_dir.exists():
        for file in sampling_dir.glob("*.png"):
            # 파일명 형식: {Benchmark}_{DB}_sampling_method_distribution_grouped.png
            name = file.stem.replace("_sampling_method_distribution_grouped", "")
            parts = name.split("_", 1)
            if len(parts) == 2:
                benchmark, db = parts
                # v7의 BIRD Dev split: DB 이름을 도메인 이름으로 변환
                if benchmark == "BIRD" and split == "Dev" and db in BIRD_DEV_DB_TO_DOMAIN:
                    db = BIRD_DEV_DB_TO_DOMAIN[db]
                
                if benchmark not in benchmarks_dbs:
                    benchmarks_dbs[benchmark] = []
                if db not in benchmarks_dbs[benchmark]:
                    benchmarks_dbs[benchmark].append(db)
    
    # 2. distribution plots에서 파일명 파싱 (v10 구조: version/split/distribution/)
    dist_dir = DISTRIBUTION_PLOTS_DIR / version / split / distribution
    if dist_dir.exists():
        for file in dist_dir.glob("*.png"):
            # 파일명 형식: {Split}_{Benchmark}_{DB}_-_{Distribution}_Distribution.png
            name = file.stem
            # {Split}_ 제거
            if name.startswith(f"{split}_"):
                name = name[len(f"{split}_"):]
            # _-_ 이후 제거
            if "_-_" in name:
                name = name.split("_-_")[0]
            parts = name.split("_", 1)
            if len(parts) == 2:
                benchmark, db = parts
                if benchmark not in benchmarks_dbs:
                    benchmarks_dbs[benchmark] = []
                if db not in benchmarks_dbs[benchmark]:
                    benchmarks_dbs[benchmark].append(db)
    
    # 3. augmented_template_distribution_plots에서 파일명 파싱 (v7 이상)
    if is_version_v7_or_above(version):
        aug_dir = AUGMENTED_TEMPLATE_PLOTS_DIR / version / "template_id_count" / split / distribution
        if aug_dir.exists():
            for file in aug_dir.glob("*.png"):
                # 파일명 형식: {Benchmark}_{DB}_augmented_template_distribution.png
                name = file.stem.replace("_augmented_template_distribution", "")
                parts = name.split("_", 1)
                if len(parts) == 2:
                    benchmark, db = parts
                    # v7의 BIRD Dev split: DB 이름을 도메인 이름으로 변환
                    if benchmark == "BIRD" and split == "Dev" and db in BIRD_DEV_DB_TO_DOMAIN:
                        db = BIRD_DEV_DB_TO_DOMAIN[db]
                    
                    if benchmark not in benchmarks_dbs:
                        benchmarks_dbs[benchmark] = []
                    if db not in benchmarks_dbs[benchmark]:
                        benchmarks_dbs[benchmark].append(db)
    
    # v16 이전 구조 호환성 (version/distribution/ - split이 파일명에 포함)
    dist_dir_old = DISTRIBUTION_PLOTS_DIR / version / distribution
    if dist_dir_old.exists():
        for file in dist_dir_old.glob(f"{split}_*.png"):
            # 파일명 형식: {Split}_{Benchmark}_{DB}_-_{Distribution}_Distribution.png
            name = file.stem
            # {Split}_ 제거
            if name.startswith(f"{split}_"):
                name = name[len(f"{split}_"):]
            # _-_ 이후 제거
            if "_-_" in name:
                name = name.split("_-_")[0]
            parts = name.split("_", 1)
            if len(parts) == 2:
                benchmark, db = parts
                # v7의 BIRD Dev split: DB 이름을 도메인 이름으로 변환
                if benchmark == "BIRD" and split == "Dev" and db in BIRD_DEV_DB_TO_DOMAIN:
                    db = BIRD_DEV_DB_TO_DOMAIN[db]
                
                if benchmark not in benchmarks_dbs:
                    benchmarks_dbs[benchmark] = []
                if db not in benchmarks_dbs[benchmark]:
                    benchmarks_dbs[benchmark].append(db)
    
    return benchmarks_dbs

# Plot 파일 경로 찾기
def find_plot_path(plot_type: str, version: str, split: str, distribution: str, benchmark: str, db: str) -> Optional[Path]:
    """Plot 파일 경로를 찾습니다.
    
    Args:
        plot_type: 'distribution', 'literal', 'sampling_method'
        version: 버전 (예: 'v16')
        split: 'Dev' 또는 'Train'
        distribution: distribution 타입 (예: 'uniform')
        benchmark: benchmark 타입 (예: 'BIRD')
        db: DB 이름 (예: 'codebase_community')
    """
    if plot_type == "distribution":
        # v10 구조: version/split/distribution/
        plot_dir = DISTRIBUTION_PLOTS_DIR / version / split / distribution
        
        # 파일명 패턴: {Split}_{Benchmark}_{DB}_-_{Distribution}_Distribution.png
        # distribution 이름을 적절히 변환 (uniform -> Uniform, zipf_query_len -> Zipf Query Len)
        dist_title = distribution.replace('_', ' ').title()
        
        # v7의 BIRD Dev split: 도메인 이름을 그대로 사용 (파일명이 이미 도메인 이름으로 되어 있음)
        # 다른 경우는 db를 그대로 사용
        search_db = db
        pattern = f"{split}_{benchmark}_{search_db}_-_{dist_title}_Distribution.png"
        file_path = plot_dir / pattern
        if file_path.exists():
            return file_path
        
        # 대체 패턴 시도 (정확한 매칭 실패 시)
        for file in plot_dir.glob(f"{split}_{benchmark}_{search_db}*.png"):
            return file
        
        # v16 이전 구조 호환성 (version/distribution/ - 파일명에 Split 포함)
        plot_dir_old = DISTRIBUTION_PLOTS_DIR / version / distribution
        if plot_dir_old.exists():
            pattern_old = f"{split}_{benchmark}_{search_db}_-_{dist_title}_Distribution.png"
            file_path_old = plot_dir_old / pattern_old
            if file_path_old.exists():
                return file_path_old
            # 대체 패턴 시도
            for file in plot_dir_old.glob(f"{split}_{benchmark}_{search_db}*.png"):
                return file
    
    elif plot_type == "sampling_method":
        plot_dir = SAMPLING_METHOD_PLOTS_DIR / version / split / distribution
        
        # v7의 BIRD Dev split: 도메인 이름을 DB 이름으로 변환하여 파일 찾기
        if benchmark == "BIRD" and split == "Dev" and db in BIRD_DOMAIN_TO_DBS:
            # 도메인에 해당하는 DB 목록에서 파일 찾기
            for db_name in BIRD_DOMAIN_TO_DBS[db]:
                file_path = plot_dir / f"{benchmark}_{db_name}_sampling_method_distribution_grouped.png"
                if file_path.exists():
                    return file_path
        
        # 일반적인 경우: 직접 파일명으로 찾기
        file_path = plot_dir / f"{benchmark}_{db}_sampling_method_distribution_grouped.png"
        if file_path.exists():
            return file_path
    
    elif plot_type == "augmented_template":
        plot_dir = AUGMENTED_TEMPLATE_PLOTS_DIR / version / "template_id_count" / split / distribution
        
        # v7의 BIRD Dev split: 도메인 이름을 DB 이름으로 변환하여 파일 찾기
        if benchmark == "BIRD" and split == "Dev" and db in BIRD_DOMAIN_TO_DBS:
            # 도메인에 해당하는 DB 목록에서 파일 찾기
            for db_name in BIRD_DOMAIN_TO_DBS[db]:
                file_path = plot_dir / f"{benchmark}_{db_name}_augmented_template_distribution.png"
                if file_path.exists():
                    return file_path
        
        # 일반적인 경우: 직접 파일명으로 찾기
        file_path = plot_dir / f"{benchmark}_{db}_augmented_template_distribution.png"
        if file_path.exists():
            return file_path
    
    return None

# Streamlit 앱
def main():
    st.set_page_config(
        page_title="Workload Analysis Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Workload Analysis Dashboard")
    st.markdown("---")
    
    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # 버전 선택
        available_versions = get_available_versions()
        if not available_versions:
            st.error("사용 가능한 버전을 찾을 수 없습니다.")
            return
        
        version = st.selectbox(
            "버전 선택",
            available_versions,
            index=0
        )
        
        # Split 선택
        available_splits = get_available_splits(version)
        if not available_splits:
            st.warning(f"버전 {version}에 사용 가능한 split이 없습니다.")
            return
        
        split = st.selectbox(
            "Split 선택",
            available_splits,
            index=0
        )
        
        # Distribution 선택
        available_distributions = get_available_distributions(version, split)
        if not available_distributions:
            st.warning(f"Split {split}에 사용 가능한 distribution이 없습니다.")
            return
        
        distribution = st.selectbox(
            "Distribution 선택",
            available_distributions,
            index=0
        )
        
        st.markdown("---")
        st.markdown(f"**현재 선택:**")
        st.markdown(f"- 버전: `{version}`")
        st.markdown(f"- Split: `{split}`")
        st.markdown(f"- Distribution: `{distribution}`")
    
    # 메인 영역
    # Benchmark와 DB 선택
    benchmarks_dbs = get_available_benchmarks_and_dbs(version, split, distribution)
    
    if not benchmarks_dbs:
        st.warning("선택한 설정에 사용 가능한 데이터가 없습니다.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        benchmark = st.selectbox(
            "Benchmark 선택",
            sorted(benchmarks_dbs.keys()),
            index=0
        )
    
    with col2:
        available_dbs = sorted(benchmarks_dbs[benchmark])
        db = st.selectbox(
            "DB 선택",
            available_dbs,
            index=0
        )
    
    st.markdown("---")
    
    # Plot 표시
    st.header(f"📈 Plots: {benchmark} - {db}")
    
    # Plot 파일 경로 찾기
    distribution_plot = find_plot_path("distribution", version, split, distribution, benchmark, db)
    sampling_method_plot = find_plot_path("sampling_method", version, split, distribution, benchmark, db)
    augmented_template_plot = None
    if is_version_v7_or_above(version):
        augmented_template_plot = find_plot_path("augmented_template", version, split, distribution, benchmark, db)
    
    # v7 이상인 경우 3개 컬럼, 그 외는 2개 컬럼
    if is_version_v7_or_above(version) and augmented_template_plot:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("📊 Distribution Comparison")
            if distribution_plot:
                try:
                    st.image(str(distribution_plot), use_container_width=True)
                except TypeError:
                    st.image(str(distribution_plot))
            else:
                st.warning("Plot을 찾을 수 없습니다.")
        
        with col2:
            st.subheader("🔍 Sampling Method Distribution")
            if sampling_method_plot:
                try:
                    st.image(str(sampling_method_plot), use_container_width=True)
                except TypeError:
                    st.image(str(sampling_method_plot))
            else:
                st.warning("Plot을 찾을 수 없습니다.")
        
        with col3:
            st.subheader("🎯 Augmented Template Distribution")
            if augmented_template_plot:
                try:
                    st.image(str(augmented_template_plot), use_container_width=True)
                except TypeError:
                    st.image(str(augmented_template_plot))
            else:
                st.warning("Plot을 찾을 수 없습니다.")
    else:
        # 2개 컬럼으로 나누어 표시
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Distribution Comparison")
            if distribution_plot:
                try:
                    st.image(str(distribution_plot), use_container_width=True)
                except TypeError:
                    st.image(str(distribution_plot))
            else:
                st.warning("Plot을 찾을 수 없습니다.")
        
        with col2:
            st.subheader("🔍 Sampling Method Distribution")
            if sampling_method_plot:
                try:
                    st.image(str(sampling_method_plot), use_container_width=True)
                except TypeError:
                    st.image(str(sampling_method_plot))
            else:
                st.warning("Plot을 찾을 수 없습니다.")
    
    # 하단 정보
    st.markdown("---")
    with st.expander("ℹ️ Plot 정보"):
        st.markdown("### Plot 설명")
        
        st.markdown("""
        **📊 Distribution Comparison**
        - Initial distribution과 Generated distribution을 비교하는 plot
        - Template rank별로 초기 분포와 실제 생성된 분포를 비교하여 샘플링이 얼마나 잘 이루어졌는지 확인
        """)
        
        st.markdown("""
        **🔍 Sampling Method Distribution**
        - Masking count별 sampling method 분포를 보여주는 plot
        - 각 masking count에서 어떤 sampling method(db, histogram, existing 등)가 사용되었는지 확인
        """)
        
        if is_version_v7_or_above(version):
            st.markdown("""
            **🎯 Augmented Template Distribution**
            - Augmented template 종류 개수별 Template ID 개수 분포를 보여주는 plot
            - X축: 사용된 Augmented template 종류 개수 (0, 1, 2, ...)
            - Y축: 해당 개수에 속하는 Template ID의 수
            - 각 template_id가 몇 종류의 augmented template을 사용했는지 분석
            """)
        
        st.markdown("### Plot 파일 경로")
        if distribution_plot:
            st.markdown(f"**Distribution Plot:** `{distribution_plot}`")
        else:
            st.markdown("**Distribution Plot:** 찾을 수 없음")
            
        if sampling_method_plot:
            st.markdown(f"**Sampling Method Plot:** `{sampling_method_plot}`")
        else:
            st.markdown("**Sampling Method Plot:** 찾을 수 없음")
            
        if is_version_v7_or_above(version):
            if augmented_template_plot:
                st.markdown(f"**Augmented Template Plot:** `{augmented_template_plot}`")
            else:
                st.markdown("**Augmented Template Plot:** 찾을 수 없음")

if __name__ == "__main__":
    main()

