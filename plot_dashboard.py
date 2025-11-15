import streamlit as st
import os
from pathlib import Path
from typing import List, Optional

# 기본 경로 설정 (상대 경로 사용)
BASE_DIR = Path(__file__).parent

# Plot 디렉토리 경로
DISTRIBUTION_PLOTS_DIR = BASE_DIR / "distribution_plots"
SAMPLING_METHOD_PLOTS_DIR = BASE_DIR / "sampling_method_distribution_plots"

# 사용 가능한 버전 목록 (디렉토리에서 자동 감지)
def get_available_versions() -> List[str]:
    """사용 가능한 버전 목록을 반환합니다."""
    versions = set()
    
    # 각 plot 디렉토리에서 버전 확인
    for plot_dir in [DISTRIBUTION_PLOTS_DIR, SAMPLING_METHOD_PLOTS_DIR]:
        if plot_dir.exists():
            for item in plot_dir.iterdir():
                if item.is_dir() and item.name.startswith('v'):
                    versions.add(item.name)
    
    return sorted(list(versions), reverse=True)  # 최신 버전부터

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
        pattern = f"{split}_{benchmark}_{db}_-_{dist_title}_Distribution.png"
        file_path = plot_dir / pattern
        if file_path.exists():
            return file_path
        
        # 대체 패턴 시도 (정확한 매칭 실패 시)
        for file in plot_dir.glob(f"{split}_{benchmark}_{db}*.png"):
            return file
        
        # v16 이전 구조 호환성 (version/distribution/ - 파일명에 Split 포함)
        plot_dir_old = DISTRIBUTION_PLOTS_DIR / version / distribution
        if plot_dir_old.exists():
            pattern_old = f"{split}_{benchmark}_{db}_-_{dist_title}_Distribution.png"
            file_path_old = plot_dir_old / pattern_old
            if file_path_old.exists():
                return file_path_old
            # 대체 패턴 시도
            for file in plot_dir_old.glob(f"{split}_{benchmark}_{db}*.png"):
                return file
    
    elif plot_type == "sampling_method":
        plot_dir = SAMPLING_METHOD_PLOTS_DIR / version / split / distribution
        # 파일명 패턴: {Benchmark}_{DB}_sampling_method_distribution_grouped.png
        file_path = plot_dir / f"{benchmark}_{db}_sampling_method_distribution_grouped.png"
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
    
    # 2종류의 plot 표시
    st.header(f"📈 Plots: {benchmark} - {db}")
    
    # Plot 파일 경로 찾기
    distribution_plot = find_plot_path("distribution", version, split, distribution, benchmark, db)
    sampling_method_plot = find_plot_path("sampling_method", version, split, distribution, benchmark, db)
    
    # 2개 컬럼으로 나누어 표시
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Distribution Comparison")
        if distribution_plot:
            try:
                st.image(str(distribution_plot), use_container_width=True)
            except TypeError:
                # 구버전 streamlit 호환성을 위해 use_container_width 제거
                st.image(str(distribution_plot))
        else:
            st.warning("Plot을 찾을 수 없습니다.")
    
    with col2:
        st.subheader("🔍 Sampling Method Distribution")
        if sampling_method_plot:
            try:
                st.image(str(sampling_method_plot), use_container_width=True)
            except TypeError:
                # 구버전 streamlit 호환성을 위해 use_container_width 제거
                st.image(str(sampling_method_plot))
        else:
            st.warning("Plot을 찾을 수 없습니다.")
    
    # 하단 정보
    st.markdown("---")
    with st.expander("ℹ️ Plot 정보"):
        st.markdown("""
        - **Distribution Comparison**: Initial distribution과 Generated distribution을 비교하는 plot
        - **Sampling Method Distribution**: Masking count별 sampling method 분포를 보여주는 plot
        """)
        
        if distribution_plot:
            st.markdown(f"**Distribution Plot 경로:** `{distribution_plot}`")
        if sampling_method_plot:
            st.markdown(f"**Sampling Method Plot 경로:** `{sampling_method_plot}`")

if __name__ == "__main__":
    main()

