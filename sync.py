"""
품고(Poomgo) → Salesforce Service Cloud 자동 동기화 스크립트
- 3개 브랜드(무스텔라, 바이오가이아, 브리오신) 출고 데이터를 가져와
  세일즈포스 원주문정보 객체에 upsert(신규 입력 or 상태 업데이트)합니다.
- 주문번호를 외부 ID로 사용해서 중복 데이터를 완전히 방지합니다.
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from poomgo_client import PoomgoClient
from salesforce_client import SalesforceClient

# ──────────────────────────────
#  로그 설정
# ──────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ──────────────────────────────
#  브랜드별 품고 API 키 설정
#  (GitHub Secrets → 환경변수로 자동 주입됨)
# ──────────────────────────────
BRANDS = [
    {"name": "무스텔라",  "api_key": os.environ["POOMGO_KEY_MUSTELA"]},
    {"name": "바이오가이아", "api_key": os.environ["POOMGO_KEY_BIOGAIA"]},
    {"name": "브리오신",  "api_key": os.environ["POOMGO_KEY_BRIOCHIN"]},
]

# 마지막 동기화 시각을 저장할 파일 경로
LAST_SYNC_FILE = Path(__file__).parent.parent / "last_sync.json"


def load_last_sync() -> dict:
    """마지막 동기화 시각을 파일에서 불러옵니다."""
    if LAST_SYNC_FILE.exists():
        with open(LAST_SYNC_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # 파일이 없으면 기본값: 7일 전부터 수집
    default_start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    return {brand["name"]: default_start for brand in BRANDS}


def save_last_sync(sync_times: dict):
    """마지막 동기화 시각을 파일에 저장합니다."""
    with open(LAST_SYNC_FILE, "w", encoding="utf-8") as f:
        json.dump(sync_times, f, ensure_ascii=False, indent=2)
    log.info(f"마지막 동기화 시각 저장 완료: {LAST_SYNC_FILE}")


def map_poomgo_to_sf(order: dict, brand_name: str) -> dict:
    """
    품고 주문 데이터 → 세일즈포스 원주문정보 객체 필드 매핑
    
    ※ 세일즈포스 필드 API 이름(오른쪽)은 실제 SF 설정에 맞게 수정해 주세요.
    """
    return {
        # 수집일자 ← 주문일시
        "REG_DATE__c": order.get("REG_DATE__c"),

        # 주문번호(쇼핑몰) ← 주문번호  [중복 방지용 외부 ID]
        "ORDER_ID__c": order.get("ORDER_ID__c"),

        # 주문번호(사방넷) ← 보조주문번호1
        "IDX__c": order.get("IDX__c"),

        # 주문자 ← 주문자명
        "USER_NAME__c": order.get("USER_NAME__c"),

        # 주문자 전화번호 ← 주문자 전화번호
        "USER_CEL__c": order.get("USER_CEL__c"),

        # 수취인 ← 수취인명
        "RECEIVE_NAME__c": order.get("RECEIVE_NAME__c"),

        # 수취인 전화번호 ← 수취인 전화번호
        "RECEIVE_CEL__c": order.get("RECEIVE_CEL__c"),

        # 수취인 주소 ← 수취인 주소
        "RECEIVE_ADDR__c": order.get("RECEIVE_ADDR__c"),

        # 상품명(수집) ← 상품명
        "PRODUCT_NAME__c": order.get("PRODUCT_NAME__c"),

        # 결제금액
        "TOTAL_COST__c": order.get("TOTAL_COST__c"),

        # 주문 상태 (취소/반품 감지용)
        "ORDER_STATUS__c": order.get("ORDER_STATUS__c"),

        # 브랜드 구분
        "BRAND_NM__c": brand_name,
    }


def run_sync():
    """메인 동기화 로직 실행"""
    log.info("=" * 60)
    log.info("품고 → 세일즈포스 동기화 시작")
    log.info("=" * 60)

    # ── 1. Salesforce 연결 ──────────────────────────
    sf_client = SalesforceClient(
        username=os.environ["SF_USERNAME"],
        password=os.environ["SF_PASSWORD"],
        security_token=os.environ["SF_SECURITY_TOKEN"],
        domain=os.environ.get("SF_DOMAIN", "login"),  # sandbox면 "test"
    )
    log.info("Salesforce 연결 완료")

    # ── 2. 마지막 동기화 시각 로드 ───────────────────
    last_sync = load_last_sync()
    new_sync_times = dict(last_sync)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    total_upserted = 0
    total_errors = 0

    # ── 3. 브랜드별 동기화 ───────────────────────────
    for brand in BRANDS:
        brand_name = brand["name"]
        api_key = brand["api_key"]
        start_date = last_sync.get(brand_name)

        log.info(f"\n[{brand_name}] 동기화 시작 (기준 시각: {start_date})")

        poomgo = PoomgoClient(api_key=api_key)

        try:
            orders = poomgo.get_all_invoices(start_date=start_date)
            log.info(f"[{brand_name}] 품고에서 {len(orders)}건 조회됨")

            if not orders:
                log.info(f"[{brand_name}] 새로운 주문 없음, 건너뜀")
                continue

            # 세일즈포스 필드 형식으로 변환
            sf_records = [map_poomgo_to_sf(o, brand_name) for o in orders]

            # Upsert: 주문번호(쇼핑몰)을 외부 ID로 사용 → 중복 방지
            upserted, errors = sf_client.upsert_orders(
                records=sf_records,
                external_id_field="Order_Number_Mall__c",  # SF 외부 ID 필드명
                object_name="Original_Order__c",            # SF 원주문정보 객체 API 이름
            )
            total_upserted += upserted
            total_errors += errors
            log.info(f"[{brand_name}] upsert 완료: 성공 {upserted}건 / 실패 {errors}건")

        except Exception as e:
            log.error(f"[{brand_name}] 동기화 중 오류 발생: {e}")
            continue

        # 성공한 브랜드만 동기화 시각 갱신
        new_sync_times[brand_name] = now_str

    # ── 4. 마지막 동기화 시각 저장 ──────────────────
    save_last_sync(new_sync_times)

    log.info("\n" + "=" * 60)
    log.info(f"동기화 완료 | 전체 upsert: {total_upserted}건 | 오류: {total_errors}건")
    log.info("=" * 60)


if __name__ == "__main__":
    run_sync()
