"""
품고(Poomgo) Open API 클라이언트
- 호스트: https://open.poomgo.com
- 인증: Authorization 헤더 (공식 문서 기준)
- 주요 엔드포인트: GET /invoice (v2) — 출고 운송장 목록 조회
"""

import logging
import time
from typing import Optional

import requests

log = logging.getLogger(__name__)

POOMGO_BASE_URL = "https://open.poomgo.com"
PAGE_SIZE = 100
RETRY_LIMIT = 3
RETRY_WAIT_SEC = 65


class PoomgoClient:
    """품고 Open API 클라이언트"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": api_key,   # ✅ 공식 문서 기준: Authorization 헤더
        })

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{POOMGO_BASE_URL}{path}"
        for attempt in range(1, RETRY_LIMIT + 1):
            try:
                response = self.session.get(url, params=params, timeout=30)
                print(f"\n[DEBUG] Full URL: {response.url}")
                print(f"[DEBUG] Status Code: {response.status_code}")
                print(f"[DEBUG] Response Text: {response.text}")

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
        params = {
            "page": page,
            "pageSize": PAGE_SIZE,
            "order": "ASC",
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
            time.sleep(0.5)

        return all_orders

    def get_invoice_status(self, order_number: str) -> Optional[str]:
        try:
            params = {"orderNumber": order_number, "pageSize": 1}
            response = self._get("/v2/invoice", params=params)
            data = response.get("data", [])
            if data:
                return data[0].get("status")
        except Exception as e:
            log.error(f"[품고] 상태 조회 실패 (주문번호: {order_number}): {e}")
        return None
