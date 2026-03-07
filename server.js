const http = require('http');
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end('<h1>秘密基地の建設完了！</h1><p>ここからChatGPTの開発者モード用MCPサーバーを作っていきます。</p>');
});
const port = process.env.PORT || 8080;
server.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});
