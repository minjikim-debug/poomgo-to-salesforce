# 품고 → Salesforce 자동 동기화 🔄

품고(Poomgo) 출고 데이터를 세일즈포스 서비스 클라우드 **원주문정보** 객체에 자동으로 입력합니다.  
취소·반품 등 상태 변경도 자동 반영되며, 중복 데이터는 원천 차단됩니다.

---

## 📁 파일 구조

```
poomgo-to-salesforce/
├── .github/
│   └── workflows/
│       └── sync.yml          ← GitHub Actions 스케줄러 (30분마다 자동 실행)
├── src/
│   ├── sync.py               ← 메인 동기화 코드
│   ├── poomgo_client.py      ← 품고 API 연결 코드
│   └── salesforce_client.py  ← 세일즈포스 연결 코드
├── requirements.txt          ← 필요한 패키지 목록
├── .env.example              ← 환경변수 예시 (참고용)
├── .gitignore
└── README.md
```

---

## 🗂️ 필드 매핑표

| 품고 필드명 | Salesforce 필드명 | Salesforce API 이름 |
|------------|-----------------|-------------------|
| 주문일시 | 수집일자 | `Collected_Date__c` |
| 주문번호 | 주문번호(쇼핑몰) | `Order_Number_Mall__c` |
| 보조주문번호1 | 주문번호(사방넷) | `Order_Number_Sabangnet__c` |
| 주문자명 | 주문자 | `Orderer_Name__c` |
| 주문자 전화번호 | 주문자 전화번호 | `Orderer_Phone__c` |
| 수취인명 | 수취인 | `Recipient_Name__c` |
| 수취인 전화번호 | 수취인 전화번호 | `Recipient_Phone__c` |
| 수취인 주소 | 수취인 주소 | `Recipient_Address__c` |
| 상품명 | 상품명(수집) | `Product_Name_Collected__c` |
| 결제금액 | 결제금액 | `Payment_Amount__c` |
| 상태 | 주문 상태 | `Order_Status__c` |

> ⚠️ **중요**: Salesforce의 실제 API 이름이 위와 다를 수 있습니다.  
> `src/sync.py` 파일의 `map_poomgo_to_sf()` 함수에서 오른쪽 값(API 이름)을 실제에 맞게 수정해 주세요.

---

## 🚀 GitHub에 올리는 방법 (처음부터 차근차근)

### 1단계: GitHub 계정 만들기
1. [github.com](https://github.com) 접속
2. 우측 상단 **Sign up** 클릭 → 가입

### 2단계: 새 저장소(Repository) 만들기
1. 로그인 후 우측 상단 **`+`** → **New repository** 클릭
2. Repository name: `poomgo-to-salesforce` 입력
3. **Private** 선택 (코드 외부 노출 방지)
4. **Create repository** 클릭

### 3단계: 코드 업로드하기
> 컴퓨터에 Git이 설치되어 있어야 합니다.  
> 없다면 [git-scm.com](https://git-scm.com/downloads)에서 설치.

터미널(윈도우: 명령 프롬프트 또는 PowerShell)을 열고 아래 명령어를 차례로 입력:

```bash
# 이 프로젝트 폴더로 이동 (폴더 위치에 맞게 수정)
cd C:\Users\내이름\Downloads\poomgo-to-salesforce

# Git 초기화
git init

# 파일 전체 추가
git add .

# 첫 번째 저장
git commit -m "첫 번째 업로드: 품고-세일즈포스 동기화"

# GitHub 저장소 연결 (★ 아래 주소는 본인 GitHub 아이디로 수정!)
git remote add origin https://github.com/[내GitHub아이디]/poomgo-to-salesforce.git

# 업로드!
git push -u origin main
```

---

### 4단계: GitHub Secrets 등록 (가장 중요! ⭐)

API 키와 비밀번호는 코드에 직접 적지 않고 GitHub Secrets에 안전하게 보관합니다.

1. GitHub 저장소 페이지 → **Settings** 탭 클릭
2. 왼쪽 메뉴 → **Secrets and variables** → **Actions**
3. **New repository secret** 버튼 클릭
4. 아래 항목을 하나씩 추가:

| Secret 이름 | 값 |
|------------|-----|
| `POOMGO_KEY_MUSTELA` | `WAOgcV5V68VQ4nOkexFf` |
| `POOMGO_KEY_BIOGAIA` | `riWUeUzjt6jOMvh9KeMq` |
| `POOMGO_KEY_BRIOSIN` | `KgEJOKo1u8xp2lToTOoJ` |
| `SF_USERNAME` | Salesforce 로그인 이메일 |
| `SF_PASSWORD` | Salesforce 비밀번호 |
| `SF_SECURITY_TOKEN` | Salesforce 보안 토큰 (아래 참고) |
| `SF_DOMAIN` | `login` (샌드박스면 `test`) |

#### Salesforce 보안 토큰 확인 방법:
1. Salesforce 접속 → 우측 상단 프로필 아이콘 클릭
2. **내 설정** → **개인** → **내 보안 토큰 초기화**
3. 이메일로 토큰이 발송됩니다

#### Salesforce API 활성화 확인:
1. Salesforce 설정 → **사용자** → API 사용 허용 체크
2. 연결된 앱(Connected App)이 필요할 수 있습니다 (자세한 건 아래 FAQ 참고)

---

### 5단계: 동기화 테스트 실행

1. GitHub 저장소 → **Actions** 탭 클릭
2. 왼쪽 메뉴에서 **품고 → Salesforce 자동 동기화** 클릭
3. **Run workflow** → **Run workflow** 버튼 클릭
4. 초록색 체크✅가 뜨면 성공!

---

### 6단계: Salesforce에서 확인
1. Salesforce Service Cloud 접속
2. **원주문정보** 객체 탭으로 이동
3. 데이터가 들어왔는지 확인!

---

## ⚠️ Salesforce 설정 체크리스트

코드를 실행하기 전에 Salesforce에서 아래 설정이 되어 있어야 합니다:

### 원주문정보 커스텀 객체에 아래 필드가 있어야 합니다:

| 필드 레이블 | API 이름 | 타입 | 비고 |
|------------|---------|------|------|
| 수집일자 | `Collected_Date__c` | DateTime | |
| 주문번호(쇼핑몰) | `Order_Number_Mall__c` | Text(80) | **외부 ID 체크 필수!** |
| 주문번호(사방넷) | `Order_Number_Sabangnet__c` | Text(80) | |
| 주문자 | `Orderer_Name__c` | Text(80) | |
| 주문자 전화번호 | `Orderer_Phone__c` | Phone | |
| 수취인 | `Recipient_Name__c` | Text(80) | |
| 수취인 전화번호 | `Recipient_Phone__c` | Phone | |
| 수취인 주소 | `Recipient_Address__c` | TextArea(255) | |
| 상품명(수집) | `Product_Name_Collected__c` | Text(255) | |
| 결제금액 | `Payment_Amount__c` | Currency | |
| 주문 상태 | `Order_Status__c` | Text(50) | |
| 브랜드 | `Brand__c` | Text(50) | |

> **외부 ID 설정 방법**: Salesforce 설정 → 개체 관리자 → 원주문정보 → 필드 및 관계  
> → `Order_Number_Mall__c` 필드 편집 → "외부 ID" 체크박스 활성화

---

## ❓ 자주 묻는 질문

**Q: 실제 Salesforce 객체/필드 이름이 다르면?**  
A: `src/sync.py`의 `map_poomgo_to_sf()` 함수와 `upsert_orders()` 호출부의  
`object_name`, `external_id_field` 값을 실제 API 이름으로 수정하면 됩니다.

**Q: 30분이 아니라 다른 주기로 변경하고 싶다면?**  
A: `.github/workflows/sync.yml`의 `cron` 값을 수정하세요.  
예) 1시간마다: `'0 0-12 * * 1-5'`

**Q: 품고 API 필드명이 정확히 무엇인가요?**  
A: `poomgo_client.py`의 `get_invoices_page()`를 실행해보면 실제 응답 필드명을 확인할 수 있습니다.  
실제 필드명에 맞게 `sync.py`의 `map_poomgo_to_sf()` 함수 왼쪽 `order.get("...")` 부분을 수정해 주세요.

**Q: Salesforce API 오류가 난다면?**  
A: 세일즈포스 연결된 앱(Connected App)에서 API 접근이 허용되어 있는지 확인하세요.  
IT 관리자가 있다면 "API 사용 허용" 권한을 요청하세요.

---

## 📞 문의
이 코드 관련 궁금한 점은 Grace CX팀에서 관리합니다.
