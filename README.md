# ER Teammate Checker

Eternal Return 隊友公開戰績查詢工具。Python 標準函式庫 + Tkinter，目標平台 Windows 10/11、Python 3.11 以上（需包含 Tcl/Tk）。不需安裝第三方 Python 套件。

## 啟動

在專案資料夾開啟 PowerShell：

```powershell
python -m er_checker --demo
```

這會啟動離線示範；按「查詢」顯示兩位虛構隊友資料。示範模式不呼叫官方 API。

正式查詢：

```powershell
python -m er_checker
```

1. 至 [官方開發者入口](https://developer.eternalreturn.io/) 申請 API 存取權限與 Key。
2. 在視窗的遮蔽欄位輸入 Key，或啟動前設定 `ER_API_KEY` 環境變數。不要將 Key 貼入 GitHub、截圖或提交到 Repo。程式不將 Key 寫入檔案、不讀取 `.env`。
3. 手動輸入 1–2 位隊友目前的遊戲暱稱，以逗號分隔；「貼上 ID」只在點擊時讀一次剪貼簿，可接受換行分隔。
4. 選一般／積分，按查詢。每位隊友有獨立頁籤，顯示近最多 20 場三人隊紀錄、勝率、平均名次、擊殺、助攻、常用角色代碼與逐場紀錄。
5. 賽季 ID 留白時只查近期紀錄；若要賽季總場次／勝場／RP，填入 **API 賽季 ID**（不等於遊戲對外顯示的賽季編號）。一般模式使用 0，積分模式使用大於 0 的 ID，可由官方 `/v2/data/Season` 確認。
6. 沒有 Key 也能按「開啟 DAK.GG」於瀏覽器查看兩位隊友的公開戰績頁。此功能不爬取 DAK.GG，也不使用其未公開 API。

## 視窗與快捷鍵

- 預設普通視窗；勾選「置頂 overlay」後變成桌面置頂視窗。可移動、調整大小。
- 預設全域快捷鍵關閉。勾選啟用後，`Ctrl+Alt+E` 顯示／隱藏視窗，`Ctrl+Alt+Q` 查詢目前輸入的 ID。
- 快捷鍵註冊失敗會顯示提示，可繼續用視窗按鈕。關閉程式會解除註冊。
- 程式無法自動知道配隊成功或隊友 ID。第一版使用手動輸入／貼上，不含 OCR。
- 建議先在桌面測試，再使用視窗化／無邊框視窗模式驗證顯示；獨占全螢幕不保證置頂視窗可見。

## 實作界線與風險

這是獨立桌面程式，僅向官方 HTTPS API 查詢公開歷史資料。使用 Windows `RegisterHotKey`，不安裝鍵盤 hook、不記錄按鍵、不模擬遊戲輸入、不讀寫遊戲記憶體、不注入 DLL、不掛接 DirectX、不攔截封包、不修改遊戲檔案，也不需要管理員權限。剪貼簿不會被背景監控，查詢結果不會持久化。

以上設計降低侵入性，但**不表示已獲官方核准，也不能保證不受反作弊系統影響**。官方對未經授權且造成不公平優勢的程式有處分規定。實際遊戲內使用前，建議將本專案用途及技術方式提交官方客服確認；目前不聲稱反作弊相容或零封鎖風險。

## 資料範圍與已知限制

- 依 2026-07-24 官方 API 文件採用 nickname → 暫時 UID → 歷史戰績；沒有使用已淘汰的 userNum 查詢。
- 官方說明歷史資料涵蓋最近 90 天，改名前的對局可能不會回傳。本程式只統計 API 當次回傳、模式符合的最新最多 20 場，不宣稱完整歷史或全賽季勝率。
- 角色目前顯示 API 角色代碼；尚未載入名稱／頭像資料。缺欄位顯示 `—`，不以 0 冒充未知數據。
- 單一背景工作循序查詢、請求間隔至少 1.1 秒、每次請求逾時 12 秒；403／429 顯示錯誤，不自動反覆重試。這是本工具節流設定，不代表官方配額。
- Key 僅送至固定官方 API 主機，拒絕 HTTP 重新導向。網路錯誤不輸出原始請求或 Key。
- 尚未使用真實 API Key 驗證，也未在遊戲執行期間測試。API 權限、真實資料格式、全域快捷鍵與遊戲中的視窗呈現需本機驗收。

## 測試

```powershell
python -m unittest discover -s tests -v
```

自動測試以模擬回應驗證 UID 路由、模式篩選、統計、部分失敗、錯誤訊息與 Key 不外洩。另見 [測試清單](docs/TESTING.md)。

## 官方參考（查核日期：2026-09-29）

- [API 文件](https://developer.eternalreturn.io/static/media/OpenAPI_EN_20260724.html)
- [API 使用條款，2026-05-21](https://support.playeternalreturn.com/hc/en-us/articles/58134893725593-API-Terms-of-Use-2026-05-21)
- [遊戲行為規範，2026-03-04](https://support.playeternalreturn.com/hc/en-us/articles/54055653655833-ETERNAL-RETURN-RULES-OF-CONDUCT-2026-03-04)
- [DAK.GG Eternal Return](https://dak.gg/er)
