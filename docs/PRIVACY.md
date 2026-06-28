#隱私與資料處理/ Privacy and Data Handling

Jobsmithyeslocal-firstdesktop/網頁app. it does not providehosted backend，但會處理履歷、職缺與求職偏好等敏感資料；公開使用前，請先了解資料會存在哪裡、何時會送到你選擇的AI後端。
##會留在本機的資料
App會把下列資料存在你的電腦：
-使用者明確儲存的候選人Profile（履歷結構化資料）-個人化偏好-已儲存的職缺搜尋結果-已產生的投遞包- BYOKSettings, unit`.env`檔-診斷錯誤紀錄，本機`error.log`

Windows `.exe`版本會盡量把app data寫在執行檔旁的`JobsmithData/`。從原始碼啟動時，預設寫到repoof`data/`目錄，除非你用環境變數覆寫。
##可能離開本機的資料
當你執行AI功能時，履歷、職缺描述、上下文與prompt會送到你選擇的AI後端：
- `claude_cli`：交給你本機已登入的Claude Code CLI處理- `codex_cli`：交給你本機已登入的Codex CLI處理- `openai`：送到你設定的OpenAI-compatible endpoint

Jobsmith本身不營運雲端資料服務。如果你設定第三方AI endpoint，該provider的資料政策會適用。
##候選人Profile

履歷解析完成後只會在目前sessionuse; to crosssession免重傳，必須在**個人化→候選人Profile**明確儲存。重新開啟App後，已儲存Profile也不會自動套用到產出，使用前需要手動選擇。
##清除個人資料
existapp內開啟**個人化→清除個人資料**，會清除：
-瀏覽器中的履歷/搜尋/ runcache-已儲存的候選人Profile與偏好-已儲存的搜尋紀錄-已產生的投遞包歷史-記憶體中的run snapshot

AI後端設定會保留，避免每次清履歷資料後都要重填API key。

##錯誤紀錄
App會把診斷錯誤寫到`error.log`。請在**setting→錯誤紀錄與回報**查看位置。回報issue時，可以貼相關錯誤訊息，但請先移除API key、履歷內容、電話、Email、公司內部資訊等敏感資料。
##職缺來源
Jobsmith會低頻查詢第三方網站的公開職缺頁面。搜尋結果可能因來源網站改版、封鎖或限流而不完整。使用者必須自行遵守各來源網站的服務條款與robots policy。

## AI生成內容
AI產生的履歷、求職信、公司情報與面試回答可能有誤。送出給雇主前，請務必人工檢查與修正。