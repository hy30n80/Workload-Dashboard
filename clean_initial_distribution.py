#!/usr/bin/env python3
"""
initial_distribution.json에서 Train-BIRD의 개별 DB 항목들을 제거하고 domain별로만 남깁니다.
"""

import json
import os

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

def clean_initial_distribution(input_file, output_file):
    """Train-BIRD에서 개별 DB 항목들을 제거합니다."""
    
    # JSON 파일 로드
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Train-BIRD의 모든 개별 DB 이름 수집
    all_train_dbs = []
    for domain_info in BIRD_DOMAIN_DBS.values():
        all_train_dbs.extend(domain_info["Train"])
    
    print(f"제거할 개별 DB 목록: {all_train_dbs}")
    
    # Train-BIRD 섹션 확인
    if "Train" in data and "BIRD" in data["Train"]:
        bird_train = data["Train"]["BIRD"]
        
        # 제거할 개별 DB 항목들
        removed_dbs = []
        for db_name in list(bird_train.keys()):
            if db_name in all_train_dbs:
                removed_dbs.append(db_name)
                del bird_train[db_name]
                print(f"✅ 제거됨: Train/BIRD/{db_name}")
        
        # Domain별 항목 확인
        domain_names = ["University", "Sport", "Software", "Financial"]
        existing_domains = []
        for domain_name in domain_names:
            if domain_name in bird_train:
                existing_domains.append(domain_name)
                print(f"✅ 유지됨: Train/BIRD/{domain_name}")
        
        print(f"\n총 {len(removed_dbs)}개 개별 DB 항목 제거됨")
        print(f"총 {len(existing_domains)}개 domain 항목 유지됨")
    else:
        print("⚠️ Train/BIRD 섹션을 찾을 수 없습니다.")
    
    # JSON 파일 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 정리된 파일이 {output_file}에 저장되었습니다.")

def main():
    input_file = "tools/distribution/initial_distribution.json"
    output_file = "tools/distribution/initial_distribution.json"
    
    print("=" * 60)
    print("Train-BIRD 개별 DB 항목 제거 시작")
    print("=" * 60)
    
    clean_initial_distribution(input_file, output_file)
    
    print("\n" + "=" * 60)
    print("정리 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()





