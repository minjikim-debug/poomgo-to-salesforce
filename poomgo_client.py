"""
품고(Poomgo) Open API 클라이언트
- 호스트: https://open.poomgo.com
- 인증: x-api-key 헤더
- 주요 엔드포인트: GET /invoice (v2) — 출고 운송장 목록 조회
"""

import logging
import time
from typing import Optional

import requests

log = logging.getLogger(__name__)

POOMGO_BASE_URL = "https://open.poomgo.com"
PAGE_SIZE = 100          # 한 번에 가져올 건수 (최대치)
RETRY_LIMIT = 3          # 429 Too Many Requests 발생 시 재시도 횟수
RETRY_WAIT_SEC = 65      # 재시도 대기 시간 (1분 + 여유)


class PoomgoClient:
    """품고 Open API 클라이언트"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "x-api-key": api_key,   # 품고 API Key 인증 헤더
        })

    def _get(self, path: str, params: dict = None) -> dict:
        """
        GET 요청 공통 처리
        - 429(Rate Limit) 발생 시 자동 재시도
        - 4xx/5xx 오류는 예외로 처리
        """
        url = f"{POOMGO_BASE_URL}{path}"
        for attempt in range(1, RETRY_LIMIT + 1):
            try:
                response = self.session.get(url, params=params, timeout=30)

                if response.status_code == 429:
                    log.warning(
                        f"[품고] Rate Limit 초과 (시도 {attempt}/{RETRY_LIMIT}), "
                        f"{RETRY_WAIT_SEC}초 후 재시도..."
                    )
                    time.sleep(RETRY_WAIT_SEC)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                if attempt == RETRY_LIMIT:
                    raise RuntimeError(f"[품고] API 호출 실패 ({url}): {e}") from e
                log.warning(f"[품고] 요청 오류 (시도 {attempt}/{RETRY_LIMIT}): {e}")
                time.sleep(5)

    def get_invoices_page(
        self,
        page: int = 1,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        """
        출고 운송장 1페이지 조회
        
        Parameters
        ----------
        page       : 페이지 번호 (1부터 시작)
        start_date : 조회 시작일시 (예: "2024-01-01T00:00:00")
        end_date   : 조회 종료일시 (예: "2024-01-31T23:59:59")
        
        Returns
        -------
        dict : 품고 페이지네이션 응답 (data, totalPages 등 포함)
        """
        params = {
            "page": page,
            "pageSize": PAGE_SIZE,
            "order": "ASC",  # 오래된 것부터 → 누락 없이 처리
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        return self._get("/v2/invoice", params=params)

    def get_all_invoices(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        """
        전체 페이지를 순회하며 모든 운송장 데이터를 반환합니다.
        
        중복 방지는 세일즈포스 upsert 단계에서 처리하지만,
        start_date를 마지막 동기화 시각으로 전달하면 불필요한 조회를 줄일 수 있습니다.
        """
        all_orders = []
        page = 1

        while True:
            log.debug(f"[품고] 페이지 {page} 요청 중...")
            response = self.get_invoices_page(
                page=page,
                start_date=start_date,
                end_date=end_date,
            )

            data = response.get("data", [])
            total_pages = response.get("totalPages", 1)
            total = response.get("total", 0)

            all_orders.extend(data)
            log.debug(
                f"[품고] 페이지 {page}/{total_pages} 완료 "
                f"(누적 {len(all_orders)}/{total}건)"
            )

            if page >= total_pages:
                break

            page += 1
            # Rate Limit 방지: 페이지 사이 잠깐 대기
            time.sleep(0.5)

        return all_orders

    def get_invoice_status(self, order_number: str) -> Optional[str]:
        """
        특정 주문번호의 현재 상태 조회 (단건)
        취소/반품 여부 확인에 사용됩니다.
        """
        try:
            params = {"orderNumber": order_number, "pageSize": 1}
            response = self._get("/v2/invoice", params=params)
            data = response.get("data", [])
            if data:
                return data[0].get("status")
        except Exception as e:
            log.error(f"[품고] 상태 조회 실패 (주문번호: {order_number}): {e}")
        return None
