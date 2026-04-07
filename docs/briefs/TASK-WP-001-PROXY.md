# Cloudflare Worker CORS Proxy 設定指南

由於 Yahoo Finance 拒絕瀏覽器的前端請求 (CORS)，你需要一個中繼代理。

## 1. 建立 Worker
1. 登入 [Cloudflare Dashboard](https://dash.cloudflare.com/)。
2. 點擊 **Workers & Pages** -> **Create application** -> **Create Worker**。
3. 命名為 `finance-proxy` 並點擊 **Deploy**。

## 2. 修改程式碼 (Edit Code)
將原本的範例代碼替換為以下內容：

```javascript
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const targetUrl = url.searchParams.get("url");

    if (!targetUrl) {
      return new Response("Missing 'url' parameter", { status: 400 });
    }

    // 允許所有來源進行 CORS
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    // 處理 OPTIONS 預檢請求
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      const response = await fetch(targetUrl, {
        method: request.method,
        headers: {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        },
      });

      const body = await response.text();
      return new Response(body, {
        status: response.status,
        headers: {
          ...corsHeaders,
          "Content-Type": response.headers.get("Content-Type") || "text/plain",
        },
      });
    } catch (e) {
      return new Response("Proxy error: " + e.message, { status: 500, headers: corsHeaders });
    }
  },
};
```

## 3. 部署與測試
- 點擊 **Save and Deploy**。
- 複製你的 Worker URL (例如 `https://finance-proxy.yourname.workers.dev/`)。
- 在 `dca_app.html` 的 **CORS Proxy** 欄位輸入該 URL。
