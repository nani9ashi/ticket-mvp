# チケット管理アプリ（Web, Django + SQLite）

BtoB業務アプリで頻出する **ワークフロー（状態遷移）・ロール認可・入力検証・監査ログ（履歴）** を最小構成で揃えた、チケット管理アプリのMVPです。

本リポジトリは「アプリ実装」側です。  
QA成果物（テスト計画／テスト設計／テストケース／結果／欠陥ログなど）は別リポジトリで管理します。

---

## 1. 目的と範囲

### 目的
- QA成果物に落とし込みやすい題材として、業務アプリの品質リスクが出やすい領域を実装する  
  - 認可（ロール×操作×フィールド）
  - 状態遷移（許可／禁止／運用制約）
  - 入力検証（必須、最大長、過去日、添付制限）
  - 監査ログ（誰がいつ何をしたか）

### 範囲
- ロール：Requester / Agent / Admin
- 画面：ログイン、チケット一覧、チケット詳細、チケット作成
- 機能：検索・ステータスフィルタ、コメント、履歴（監査ログ）、担当割当（Admin）、ステータス変更（Agent担当のみ/Admin）
- 添付：作成時のみ、1ファイル、拡張子／サイズ制限

---

## 2. 技術スタック

- Python / Django
- SQLite（開発用）
- Django標準認証（ログイン）

---

## 3. セットアップ（Windows / PowerShell）

### 3.1 仮想環境の作成・有効化
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install django
```

### 3.2 DB初期化とデモデータ投入
```powershell
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

起動後：
- ログイン：`http://127.0.0.1:8000/accounts/login/`
- 一覧：`http://127.0.0.1:8000/`

---

## 4. デモユーザー（seed_demo）

`python manage.py seed_demo` で以下を作成します。  
全ユーザーのパスワードは **`pass1234`** です。

- Requester：`requester1`, `requester2`
- Agent：`agent1`, `agent2`
- Admin（アプリロール）：`admin1`

> 注意：`admin1` は「アプリ内ロール（Adminグループ）」のユーザーです。  
> Django管理画面（/admin/）へ入る `createsuperuser` のユーザーとは別です。

---

## 5. ロールと権限

### Requester（依頼者）
- 自分のチケットのみ：作成・閲覧・コメント可
- ステータス変更／担当割当／期限変更：不可

### Agent（担当者）
- 全チケット閲覧可
- **担当チケットのみ**：ステータス変更可
- コメント：可
- 担当割当／期限変更：不可

### Admin（管理者）
- 全チケット閲覧・更新可
- 担当割当：可
- 期限設定／変更：可

---

## 6. ステータス遷移

許可：
- Open → In Progress / Pending
- In Progress → Resolved / Pending
- Pending → In Progress
- Resolved → Closed

禁止：
- Open → Closed
- Closed →（いかなる遷移も）禁止

運用制約：
- ステータス変更は Agent（担当のみ）または Admin のみ
- **担当未割当のチケットは Agent がステータス変更できない**（Adminが割当後に運用）

---

## 7. 入力検証

- Title：必須、最大80文字
- Body：必須、最大4000文字
- Due date：任意、過去日不可（Adminのみ設定/変更）
- Attachment：任意、1ファイル、拡張子制限（png/jpg/jpeg/pdf/txt）、最大5MB  
  - 添付は作成時のみ（差し替え／削除は不可）

---

## 8. 監査ログ（履歴）

チケット詳細画面で履歴を確認できます。  
MVPでは主に以下の操作を記録します。

- CREATED
- STATUS_CHANGED
- ASSIGNEE_CHANGED
- COMMENT_ADDED
- （導入している場合）DUE_DATE_CHANGED

---

## 9. テスト用の意図的欠陥

本リポジトリには、QA検証の題材として **意図的欠陥を再現するスイッチ**を用意しています。

### INTENTIONAL_BUG_IDOR
- `True` の場合：閲覧認可が崩れ、Requesterが他人チケットを閲覧できる状態を再現します（IDOR想定）
- `False` の場合：通常の認可（Requesterは自分のチケットのみ）

設定例（`config/settings.py`）：
```python
INTENTIONAL_BUG_IDOR = False
```

> QA成果物側では「どのコミット/設定でテストしたか」を記録し、再現性を担保します。

---

## 10. 開発・運用メモ

### DBを初期状態へ戻す（開発用）
```powershell
Remove-Item .\db.sqlite3
python manage.py migrate
python manage.py seed_demo
```

### 添付ファイル
添付は `media/` 配下に保存されます（Git管理対象外）。

---

## 11. 関連（QA成果物リポジトリ）
- QA成果物（テスト設計、テストケース、テスト結果、欠陥ログ等）は別リポジトリにて管理
- 本アプリの特定バージョン（タグ/コミット）に対してテストを実施します
