# ER Teammate Checker

Eternal Return 隊友公開戰績工具。**不用打韓文、不需要官方 API Key**：框選名稱 → 本機多語 OCR → 背景瀏覽器查詢 DAK.GG → Tkinter 視窗顯示戰績。

## 快速開始

需要 Windows 10/11、Python 3.11 以上（含 Tcl/Tk）及 Microsoft Edge。已在 Python 3.14 驗證。

在專案資料夾執行一次：

```powershell
python tools/setup_runtime.py
```

也可執行 `./setup.ps1`。安裝會建立 `.venv`，安裝 Pillow / Playwright，下載 Tesseract 與韓／英／繁中／簡中／日文模型到 `.tools`。固定版本並核對 SHA256；安裝檔只用來解壓，不執行安裝器、不改系統 PATH，不需要管理員權限。首次需要網路，之後 OCR 完全離線。大型模型、執行檔與個人設定不提交 Git。

雙擊 **start.cmd**，或：

```powershell
./.venv/Scripts/python.exe -m er_checker
```

## 實際操作

1. 遊戲顯示隊友名稱時，按「① 框選名稱位置」。工具暫時隱藏，顯示桌面快照。
2. 拖曳框住第一位隊友的**整行名稱**，再框第二位；不要包含頭像、段位或其他文字。最多兩格，**Enter** 完成、右鍵重選、**Esc** 取消。
3. 程式自動比較韓文、英文、繁體中文、簡體中文、日文。候選分數高且差距足夠時，自動查詢 DAK.GG。
4. 不確定時停在截圖預覽與候選清單。看字形直接選另一個候選，再按「查詢」，**不需要打韓文**；也可重框或改「韓文優先」重試。
5. 框選位置記在 `.local/regions.json`。下次配隊按「② 截圖辨識」，或啟用快捷鍵後按 **Ctrl+Alt+Q**，就會截取相同位置的新名稱。

沒有開遊戲也能測試：按「匯入截圖」，選 PNG/JPG/BMP/WebP，再框選名称。匯入圖片不改桌面座標；圖片只在本機處理，不會上傳。

座標依 Windows 虛擬桌面記錄（含左側副螢幕）。顯示器配置／解析度改變會要求重框；移動遊戲視窗或改遊戲 UI 縮放也應重框。建議使用無邊框或視窗化，獨占全螢幕可能黑屏或無法顯示工具。

## 功能與範圍

- 預設 **DAK.GG**，不用登入 API Portal。
- 上方為網站預設賽季的**積分摘要**：RP、勝率、場次、平均擊殺／助攻／傷害、常用角色。
- 「角色統計／排序」讀取完整角色明細，列出場次、累積 RP、場均 RP、勝率、平均擊殺與傷害。**場均 RP＝該角色累積 RP ÷ 場次，至少 3 場才顯示**；不足樣本或缺資料置於排序末尾。RP 保留正負號。
- 點角色表格的任一欄名切換升／降冪：依場次找最常玩、依累積 RP 找加分最多、依場均 RP 比較每場表現；箭頭表示目前方向。預設依場次由多到少，排序不會跨玩家混合。
- 「近 20 場模式／組隊」另讀**全部模式**的最新最多 20 場，顯示各模式場次與比例；不足 20 場按實際筆數計算，與目前選擇的積分／一般篩選分開。
- **多排目前無法可靠判定**：查核到的公開頁面沒有可驗證的單／雙／三排標記。同隊次數不能證明預組隊，`T 2` 的滑鼠提示為 `TERMINATE 2`，也不是雙排。本工具不將缺少標記當作單排。
- 積分／一般切換的是**下方近期對局**；不把積分賽季摘要當成一般模式統計。
- 最多顯示當次網站載入的 20 場：名次、角色、TK、擊殺、助攻、傷害、時間。**TK 是隊伍擊殺，不是死亡次數。**
- 顯示網站更新時間、本機讀取時間；網站資料可能延遲，賽季名稱取不到時明示。
- 可勾選置頂 overlay；啟用全域快捷鍵後，Ctrl+Alt+E 顯示／隱藏、Ctrl+Alt+Q 截圖辨識。首次沒有座標時進入框選。
- 工作中不接受另一個工作；「取消工作」停止後續操作。當前網路請求可能要等返回／逾時才結束；關閉視窗也會要求背景瀏覽器清理退出。
- 保留手動輸入／貼上、開啟完整網頁與「官方 API」備用來源。僅選官方 API 才需要 Key；Key 不寫入設定。API 賽季 ID 不等於遊戲對外賽季編號。
- `start.cmd --demo` 使用虛構戰績，不呼叫戰績網站。OCR 仍是真實本機辨識；開啟網頁按鈕仍可啟動瀏覽器。

## OCR 與網站限制

原型的 OCR **不是百分之百準確**。遊戲字型、特殊符號、描邊、縮放、動畫、背景與 I/l/1 可能造成錯字。分數為 OCR 參考值，不是正確率。每個名稱輪流比較五個語言模型及兩種影像處理結果；不依賴 Windows 輸入法。候選第一名分數至少 75 且比第二名高至少 8 才自動查詢；你可關閉自動查詢。沒有候選正確時需重框，不會大量查詢所有候選。

DAK.GG 使用 Playwright 啟動**獨立 headless Edge**，只讀公開玩家頁的已渲染 DOM，不使用使用者登入設定、不呼叫未公開 API。每位玩家讀取模式頁、角色明細頁及全部模式頁；每次導航間隔至少 3 秒，同玩家／模式在記憶體快取 120 秒（最多 32 組），不主動按網站更新按鈕。新增明細會增加首次查詢時間。

查詢前檢查 robots.txt，不能讀取或不允許就停止。2026-09-29 查核時 `/er/search/players` 被禁止；本工具只使用 `/er/players/{nickname}`。robots.txt 不等於使用授權，網站規範仍可能變更。403、429、驗證頁、玩家不符、未載入或解析失敗會顯示錯誤／部分資料提示，保留「開啟網頁」供手動查看，不破解驗證、不無限重試。

## 遊戲互動與隱私

僅使用一般桌面截圖、Windows RegisterHotKey、獨立 Tkinter 視窗與外部瀏覽器。不讀寫遊戲記憶體、不注入 DLL、不掛接 DirectX、不攔截封包、不記錄鍵盤、不模擬遊戲輸入、不修改遊戲檔案。只在使用者按按鈕／快捷鍵時截圖，不連續背景監控。

日常只截取已選名稱区域；初次框選需要全桌面快照，均僅留在記憶體。網站只收到辨識出的遊戲暱稱。正式程式不存截圖或查詢紀錄；本機設定僅含座標與螢幕範圍。

**不代表官方已核准，也不保證零封鎖風險。** 實際遊戲內相容性與辨識率需使用者測試；第三方程式的判定仍以官方規範／回覆為準。

## 驗證

已驗證韓文、英文、繁中、日文、韓文加數字的合成字型樣本；另將兩個韓文名稱顯示在測試視窗，實際走過**桌面截圖 → OCR → 真實 DAK.GG → 雙頁籤各 20 場**。一般模式也取得 20 場，與積分分開。這是測試字型／視窗，**不是遊戲畫面的辨識成功率測試**；未進入遊戲驗收。

```powershell
./.venv/Scripts/python.exe -m unittest discover -s tests -v
./.venv/Scripts/python.exe -c "import runpy; runpy.run_path('tests/gui_smoke.py')"
./.venv/Scripts/python.exe -c "import runpy; runpy.run_path('tests/gui_analytics_smoke.py')"
./.venv/Scripts/python.exe tools/check_runtime.py
# 以下會讀取少量真實公開戰績：
./.venv/Scripts/python.exe tools/check_runtime.py --live --normal
./.venv/Scripts/python.exe tools/qa_workflow.py --live
```

QA 會短暫顯示測試名稱視窗，將本工具 UI 圖片與報告存於 `artifacts/`（Git 忽略）。日常程式不會存圖。完整驗收清單見 [docs/TESTING.md](docs/TESTING.md)。

## 參考與依賴

- [DAK.GG](https://dak.gg/er) / [網站條款](https://dak.gg/about/agreement?hl=en) / [robots.txt](https://dak.gg/robots.txt)
- [Tesseract](https://github.com/tesseract-ocr/tesseract) / [語言模型](https://github.com/tesseract-ocr/tessdata_fast)（Apache-2.0）
- [7-Zip 授權](https://www.7-zip.org/license.txt)（setup 解壓用途，授權文件隨套件保留）
- [Pillow](https://python-pillow.org/) / [Playwright](https://playwright.dev/python/)
- [官方 API 文件](https://developer.eternalreturn.io/static/media/OpenAPI_EN_20260724.html)
- [API 條款](https://support.playeternalreturn.com/hc/en-us/articles/58134893725593-API-Terms-of-Use-2026-05-21) / [遊戲行為規範](https://support.playeternalreturn.com/hc/en-us/articles/54055653655833-ETERNAL-RETURN-RULES-OF-CONDUCT-2026-03-04)
